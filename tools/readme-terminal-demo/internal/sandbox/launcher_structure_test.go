package sandbox

import (
	"bufio"
	"go/ast"
	"go/parser"
	"go/token"
	"os"
	"os/exec"
	"regexp"
	"strconv"
	"strings"
	"testing"
)

func TestTerminalSourceStructure(t *testing.T) {
	terminal := functionSourceFrom(t, "exec_linux.go", "executePrepared")
	requireOrdered(t, terminal,
		"runtime.LockOSThread()",
		"rawGetTID()",
		"closeInheritedExcept(preparedPtr.rulesetFD)",
		"rawNoNewPrivs()",
		"rawLandlockRestrictSelf(preparedPtr.rulesetFD, 0)",
		"rawCloseFD(preparedPtr.rulesetFD)",
		"rawGetTID()",
		"unix.RawSyscall(unix.SYS_EXECVE",
		"runtime.KeepAlive(preparedPtr)",
		"exitGroup(executionFailureExitCode)",
	)

	terminalFunctions := []struct {
		filename string
		name     string
		allowed  map[string]bool
	}{
		{
			filename: "exec_linux.go",
			name:     "executePrepared",
			allowed: allowedTerminalCalls(
				"runtime.LockOSThread", "rawGetTID", "exitGroup", "rawCloseRangeCall",
				"closeInheritedExcept", "rawNoNewPrivs", "rawLandlockRestrictSelf",
				"rawCloseFD", "unix.RawSyscall", "uintptr", "uint32", "unsafe.Pointer",
				"runtime.KeepAlive",
			),
		},
		{
			filename: "fds_linux.go",
			name:     "closeInheritedExcept",
			allowed:  allowedTerminalCalls("rawCloseRangeCall", "uint32"),
		},
		{
			filename: "fds_linux.go",
			name:     "rawCloseRangeCall",
			allowed:  allowedTerminalCalls("unix.RawSyscall", "uintptr"),
		},
		{
			filename: "exec_linux.go",
			name:     "rawGetTID",
			allowed:  allowedTerminalCalls("unix.RawSyscall"),
		},
		{
			filename: "exec_linux.go",
			name:     "rawNoNewPrivs",
			allowed:  allowedTerminalCalls("unix.RawSyscall6", "uintptr"),
		},
		{
			filename: "exec_linux.go",
			name:     "rawLandlockRestrictSelf",
			allowed:  allowedTerminalCalls("unix.RawSyscall", "uintptr"),
		},
		{
			filename: "exec_linux.go",
			name:     "rawCloseFD",
			allowed:  allowedTerminalCalls("unix.RawSyscall", "uintptr"),
		},
		{
			filename: "exec_linux.go",
			name:     "exitGroup",
			allowed:  allowedTerminalCalls("unix.RawSyscall", "uintptr"),
		},
	}
	for _, function := range terminalFunctions {
		declaration := functionDeclarationFrom(t, function.filename, function.name)
		requireRawTerminalFunction(t, function.name, declaration, function.allowed)
	}

	execute := functionDeclarationFrom(t, "exec_linux.go", "executePrepared")
	requireNoOrdinaryReturn(t, execute)
	requireDirectExecvePointers(t, execute)
	requireSingleKeepAlive(t, execute)
	requirePreparedExecStoresNoUintptr(t)
	requireProductionFaultNone(t)
	requireProductionCloseUsesRawWrapper(t)
	requireNoReturningRestrictionPath(t)
	requireRawPreflightBoundary(t)

	if strings.Contains(fileSource(t, "exec_linux.go"), "os.Getenv") {
		t.Fatal("terminal fault is controllable through the environment")
	}
}

func TestTerminalEscapeAnalysis(t *testing.T) {
	execute := functionDeclarationFrom(t, "exec_linux.go", "executePrepared")
	requireSingleKeepAlive(t, execute)
	for _, filename := range []string{"exec_linux.go", "fds_linux.go"} {
		for _, forbidden := range []string{"//go:noescape", "//go:uintptrescapes", "//go:linkname"} {
			if strings.Contains(fileSource(t, filename), forbidden) {
				t.Fatalf("%s contains forbidden escape workaround %q", filename, forbidden)
			}
		}
	}

	spans := []terminalDiagnosticSpan{
		terminalFunctionSpan(t, "exec_linux.go", "executePrepared"),
		terminalFunctionSpan(t, "fds_linux.go", "closeInheritedExcept"),
		terminalFunctionSpan(t, "fds_linux.go", "rawCloseRangeCall"),
		terminalFunctionSpan(t, "exec_linux.go", "rawGetTID"),
		terminalFunctionSpan(t, "exec_linux.go", "rawNoNewPrivs"),
		terminalFunctionSpan(t, "exec_linux.go", "rawLandlockRestrictSelf"),
		terminalFunctionSpan(t, "exec_linux.go", "rawCloseFD"),
		terminalFunctionSpan(t, "exec_linux.go", "exitGroup"),
	}

	command := exec.Command("go", "test", "-run", "^$", "-gcflags=all=-m=2", ".")
	command.Env = append(os.Environ(), "GOCACHE="+t.TempDir())
	output, err := command.CombinedOutput()
	if err != nil {
		t.Fatalf("run terminal escape analysis: %v; output=%s", err, output)
	}

	diagnosticPattern := regexp.MustCompile(`(?:^|[/\\])([^/\\:]+\.go):([0-9]+):[0-9]+:\s+(.*)$`)
	seen := make(map[string]bool, len(spans))
	scanner := bufio.NewScanner(strings.NewReader(string(output)))
	scanner.Buffer(make([]byte, 4096), 1024*1024)
	for scanner.Scan() {
		match := diagnosticPattern.FindStringSubmatch(scanner.Text())
		if match == nil {
			continue
		}
		line, conversionErr := strconv.Atoi(match[2])
		if conversionErr != nil {
			t.Fatalf("parse compiler diagnostic line %q: %v", match[2], conversionErr)
		}
		for _, span := range spans {
			if match[1] != span.filename || line < span.firstLine || line > span.lastLine {
				continue
			}
			seen[span.name] = true
			message := match[3]
			for _, forbidden := range []string{"escapes to heap", "moved to heap", "leaking param", "leaks to heap"} {
				if strings.Contains(message, forbidden) {
					t.Errorf("terminal compiler diagnostic for %s: %s", span.name, message)
				}
			}
		}
	}
	if err := scanner.Err(); err != nil {
		t.Fatalf("scan compiler diagnostics: %v", err)
	}
	for _, span := range spans {
		if !seen[span.name] {
			t.Errorf("compiler emitted no mapped diagnostic for terminal span %s", span.name)
		}
	}
}

type terminalDiagnosticSpan struct {
	filename  string
	name      string
	firstLine int
	lastLine  int
}

func terminalFunctionSpan(t *testing.T, filename, name string) terminalDiagnosticSpan {
	t.Helper()

	source := []byte(fileSource(t, filename))
	files, declaration := parseFunction(t, filename, source, name)
	return terminalDiagnosticSpan{
		filename:  filename,
		name:      name,
		firstLine: files.Position(declaration.Pos()).Line,
		lastLine:  files.Position(declaration.End()).Line,
	}
}

func allowedTerminalCalls(names ...string) map[string]bool {
	allowed := make(map[string]bool, len(names))
	for _, name := range names {
		allowed[name] = true
	}
	return allowed
}

func requireRawTerminalFunction(t *testing.T, name string, declaration *ast.FuncDecl, allowed map[string]bool) {
	t.Helper()

	ast.Inspect(declaration.Body, func(node ast.Node) bool {
		switch typed := node.(type) {
		case *ast.DeferStmt:
			t.Errorf("%s contains forbidden defer", name)
		case *ast.GoStmt:
			t.Errorf("%s contains forbidden goroutine handoff", name)
		case *ast.FuncLit:
			t.Errorf("%s contains forbidden cleanup callback or fallback", name)
		case *ast.InterfaceType:
			t.Errorf("%s contains forbidden interface boxing", name)
		case *ast.CallExpr:
			called := calledFunctionName(typed.Fun)
			if !allowed[called] {
				t.Errorf("%s calls forbidden terminal operation %q", name, called)
			}
		}
		return true
	})
}

func calledFunctionName(expression ast.Expr) string {
	switch called := expression.(type) {
	case *ast.Ident:
		return called.Name
	case *ast.SelectorExpr:
		if packageName, ok := called.X.(*ast.Ident); ok {
			return packageName.Name + "." + called.Sel.Name
		}
		return called.Sel.Name
	default:
		return "<dynamic>"
	}
}

func requireNoOrdinaryReturn(t *testing.T, declaration *ast.FuncDecl) {
	t.Helper()

	ast.Inspect(declaration.Body, func(node ast.Node) bool {
		if _, ok := node.(*ast.ReturnStmt); ok {
			t.Error("executePrepared contains forbidden ordinary return")
		}
		return true
	})
}

func requireDirectExecvePointers(t *testing.T, declaration *ast.FuncDecl) {
	t.Helper()

	var execveCalls []*ast.CallExpr
	allowedPointerConversions := make(map[token.Pos]bool)
	ast.Inspect(declaration.Body, func(node ast.Node) bool {
		call, ok := node.(*ast.CallExpr)
		if !ok || calledFunctionName(call.Fun) != "unix.RawSyscall" || len(call.Args) != 4 ||
			expressionName(call.Args[0]) != "unix.SYS_EXECVE" {
			return true
		}
		execveCalls = append(execveCalls, call)
		for _, argument := range call.Args[1:] {
			if !isDirectUnsafeUintptr(argument) {
				t.Errorf("SYS_EXECVE pointer argument is not a direct uintptr(unsafe.Pointer(...)) conversion")
				continue
			}
			allowedPointerConversions[argument.Pos()] = true
		}
		return true
	})
	if len(execveCalls) != 1 {
		t.Fatalf("executePrepared has %d raw SYS_EXECVE calls; want exactly 1", len(execveCalls))
	}

	ast.Inspect(declaration.Body, func(node ast.Node) bool {
		call, ok := node.(*ast.CallExpr)
		if ok && isDirectUnsafeUintptr(call) && !allowedPointerConversions[call.Pos()] {
			t.Error("executePrepared caches or uses an unsafe uintptr conversion outside the SYS_EXECVE call")
		}
		return true
	})
}

func isDirectUnsafeUintptr(expression ast.Expr) bool {
	outer, ok := expression.(*ast.CallExpr)
	if !ok || calledFunctionName(outer.Fun) != "uintptr" || len(outer.Args) != 1 {
		return false
	}
	inner, ok := outer.Args[0].(*ast.CallExpr)
	return ok && calledFunctionName(inner.Fun) == "unsafe.Pointer" && len(inner.Args) == 1
}

func expressionName(expression ast.Expr) string {
	switch value := expression.(type) {
	case *ast.Ident:
		return value.Name
	case *ast.SelectorExpr:
		if packageName, ok := value.X.(*ast.Ident); ok {
			return packageName.Name + "." + value.Sel.Name
		}
		return value.Sel.Name
	default:
		return ""
	}
}

func requireSingleKeepAlive(t *testing.T, declaration *ast.FuncDecl) {
	t.Helper()

	var keepAliveCalls []*ast.CallExpr
	var execvePosition, executionExitPosition token.Pos
	ast.Inspect(declaration.Body, func(node ast.Node) bool {
		call, ok := node.(*ast.CallExpr)
		if !ok {
			return true
		}
		switch calledFunctionName(call.Fun) {
		case "runtime.KeepAlive":
			keepAliveCalls = append(keepAliveCalls, call)
		case "unix.RawSyscall":
			if len(call.Args) == 4 && expressionName(call.Args[0]) == "unix.SYS_EXECVE" {
				execvePosition = call.Pos()
			}
		case "exitGroup":
			if len(call.Args) == 1 && expressionName(call.Args[0]) == "executionFailureExitCode" {
				executionExitPosition = call.Pos()
			}
		}
		return true
	})
	if len(keepAliveCalls) != 1 {
		t.Fatalf("executePrepared has %d runtime.KeepAlive calls; want exactly 1", len(keepAliveCalls))
	}
	call := keepAliveCalls[0]
	if len(call.Args) != 1 || expressionName(call.Args[0]) != "preparedPtr" {
		t.Fatal("the sole liveness barrier is not runtime.KeepAlive(preparedPtr)")
	}
	if execvePosition == token.NoPos || executionExitPosition == token.NoPos ||
		!(execvePosition < call.Pos() && call.Pos() < executionExitPosition) {
		t.Fatal("runtime.KeepAlive(preparedPtr) is not exactly between returned execve and exit-group 5")
	}
}

func requirePreparedExecStoresNoUintptr(t *testing.T) {
	t.Helper()

	parsed := parseFile(t, "exec_linux.go")
	for _, declaration := range parsed.Decls {
		general, ok := declaration.(*ast.GenDecl)
		if !ok || general.Tok != token.TYPE {
			continue
		}
		for _, specification := range general.Specs {
			typeSpec, ok := specification.(*ast.TypeSpec)
			if !ok || typeSpec.Name.Name != "preparedExec" {
				continue
			}
			structure, ok := typeSpec.Type.(*ast.StructType)
			if !ok {
				t.Fatal("preparedExec is not a struct")
			}
			ast.Inspect(structure, func(node ast.Node) bool {
				if identifier, ok := node.(*ast.Ident); ok && identifier.Name == "uintptr" {
					t.Error("preparedExec stores forbidden cached uintptr data")
				}
				return true
			})
			return
		}
	}
	t.Fatal("preparedExec type declaration not found")
}

func requireProductionFaultNone(t *testing.T) {
	t.Helper()

	declaration := functionDeclarationFrom(t, "exec_linux.go", "prepareRestrictedExecWithOps")
	found := false
	ast.Inspect(declaration.Body, func(node ast.Node) bool {
		literal, ok := node.(*ast.CompositeLit)
		if !ok || expressionName(literal.Type) != "preparedExec" {
			return true
		}
		for _, element := range literal.Elts {
			keyValue, ok := element.(*ast.KeyValueExpr)
			if !ok || expressionName(keyValue.Key) != "fault" {
				continue
			}
			found = expressionName(keyValue.Value) == "terminalFaultNone"
		}
		return true
	})
	if !found {
		t.Fatal("production preparation does not pin terminalFaultNone")
	}
}

func requireProductionCloseUsesRawWrapper(t *testing.T) {
	t.Helper()

	production := functionSourceFrom(t, "fds_linux.go", "closeInheritedExcept")
	if strings.Contains(production, "closeInheritedExceptWith") {
		t.Error("production descriptor close routes through the injectable test seam")
	}
	requireOrdered(t, production,
		"rawCloseRangeCall(uint32(rulesetFD+1), ^uint32(0), unix.CLOSE_RANGE_UNSHARE)",
		"rulesetFD > 3",
		"rawCloseRangeCall(3, uint32(rulesetFD-1), 0)",
	)
	if strings.Count(production, "rawCloseRangeCall(") != 2 {
		t.Errorf("production descriptor close has %d raw wrapper calls; want 2", strings.Count(production, "rawCloseRangeCall("))
	}
}

func requireNoReturningRestrictionPath(t *testing.T) {
	t.Helper()

	parsed := parseFile(t, "landlock_linux.go")
	for _, declaration := range parsed.Decls {
		function, ok := declaration.(*ast.FuncDecl)
		if !ok {
			continue
		}
		switch function.Name.Name {
		case "RestrictV3", "applyPreparedV3":
			t.Errorf("production retains forbidden returning restriction path %s", function.Name.Name)
		}
	}
}

func requireRawPreflightBoundary(t *testing.T) {
	t.Helper()

	preflight := functionSourceFrom(t, "exec_linux.go", "prepareRestrictedExecWithOps")
	for _, required := range []string{
		"validateExecPath(spec.Path)",
		"validateExecArgs(spec.Path, spec.Args)",
		"validateExecEnvironment(spec.Env)",
		"ownedCString(spec.Path)",
		"ownedCStringVector(spec.Args)",
		"ownedCStringVector(spec.Env)",
		"prepareV3WithOps(spec.Policy, ops)",
	} {
		if !strings.Contains(preflight, required) {
			t.Errorf("prepareRestrictedExecWithOps is missing fallible preflight %q", required)
		}
	}
	if strings.Contains(preflight, "runtime.LockOSThread") {
		t.Error("prepareRestrictedExecWithOps locks the OS thread before fallible preflight completes")
	}

	launcher := functionSourceFrom(t, "exec_linux.go", "ExecRestricted")
	requireOrdered(t, launcher,
		"prepareRestrictedExec(spec)",
		"executePrepared(preparedPtr)",
		"exitGroup(runtimeFailureExitCode)",
	)
}

func requireOrdered(t *testing.T, source string, fragments ...string) {
	t.Helper()

	next := 0
	for _, fragment := range fragments {
		relative := strings.Index(source[next:], fragment)
		if relative < 0 {
			t.Fatalf("source is missing %q after byte %d", fragment, next)
		}
		next += relative + len(fragment)
	}
}

func functionSourceFrom(t *testing.T, filename, name string) string {
	t.Helper()

	source := fileSource(t, filename)
	files, declaration := parseFunction(t, filename, []byte(source), name)
	start := files.Position(declaration.Pos()).Offset
	end := files.Position(declaration.End()).Offset
	return source[start:end]
}

func functionDeclarationFrom(t *testing.T, filename, name string) *ast.FuncDecl {
	t.Helper()

	source := []byte(fileSource(t, filename))
	_, declaration := parseFunction(t, filename, source, name)
	return declaration
}

func fileSource(t *testing.T, filename string) string {
	t.Helper()

	source, err := os.ReadFile(filename)
	if err != nil {
		t.Fatalf("read %s: %v", filename, err)
	}
	return string(source)
}

func parseFile(t *testing.T, filename string) *ast.File {
	t.Helper()

	parsed, err := parser.ParseFile(token.NewFileSet(), filename, fileSource(t, filename), 0)
	if err != nil {
		t.Fatalf("parse %s: %v", filename, err)
	}
	return parsed
}

func parseFunction(t *testing.T, filename string, source []byte, name string) (*token.FileSet, *ast.FuncDecl) {
	t.Helper()

	files := token.NewFileSet()
	parsed, err := parser.ParseFile(files, filename, source, 0)
	if err != nil {
		t.Fatalf("parse %s: %v", filename, err)
	}
	for _, declaration := range parsed.Decls {
		function, ok := declaration.(*ast.FuncDecl)
		if !ok || function.Name.Name != name {
			continue
		}
		return files, function
	}
	t.Fatalf("%s declaration not found", name)
	return nil, nil
}

// Package tape parses behavior-only VHS tapes and composes trusted presentation.
//
// A plugin-owned tape declares interaction behavior and nothing else. Every
// presentation control, the output destination, and the shell originate from
// typed configuration held by this package, never from tape text. Parsing is
// data-only: it never invokes a shell, VHS, the filesystem, the environment,
// or the network, and it never matches a wait pattern.
package tape

import (
	"bufio"
	"errors"
	"fmt"
	"io"
	"regexp"
	"strconv"
	"strings"
	"time"
	"unicode/utf8"

	"github.com/z-shell/.github/tools/readme-terminal-demo/internal/failure"
	"github.com/z-shell/.github/tools/readme-terminal-demo/internal/limits"
)

// Kind is the closed set of directives the v1 contract accepts.
type Kind string

const (
	KindType       Kind = "Type"
	KindEnter      Kind = "Enter"
	KindTab        Kind = "Tab"
	KindSpace      Kind = "Space"
	KindBackspace  Kind = "Backspace"
	KindLeft       Kind = "Left"
	KindRight      Kind = "Right"
	KindUp         Kind = "Up"
	KindDown       Kind = "Down"
	KindPageUp     Kind = "PageUp"
	KindPageDown   Kind = "PageDown"
	KindScrollUp   Kind = "ScrollUp"
	KindScrollDown Kind = "ScrollDown"
	KindCtrl       Kind = "Ctrl"
	KindSleep      Kind = "Sleep"
	KindWait       Kind = "Wait"
	KindWaitLine   Kind = "Wait+Line"
	KindWaitScreen Kind = "Wait+Screen"
)

// repeatableKeys is the closed set of directives accepting an optional count.
var repeatableKeys = map[Kind]struct{}{
	KindEnter:      {},
	KindTab:        {},
	KindSpace:      {},
	KindBackspace:  {},
	KindLeft:       {},
	KindRight:      {},
	KindUp:         {},
	KindDown:       {},
	KindPageUp:     {},
	KindPageDown:   {},
	KindScrollUp:   {},
	KindScrollDown: {},
}

// waitKinds is the closed set of wait directives and their tape spellings.
var waitKinds = map[string]Kind{
	"Wait":        KindWait,
	"Wait+Line":   KindWaitLine,
	"Wait+Screen": KindWaitScreen,
}

// Directive is one validated behavior instruction.
type Directive struct {
	Kind     Kind
	Text     string
	Count    int
	Duration time.Duration
	Pattern  string
	Line     int
}

// Config holds the trusted presentation contract. It lives in package tape so
// that render may depend on tape without creating an import cycle.
type Config struct {
	Width       int
	Height      int
	FontFamily  string
	FontSize    int
	Theme       string
	Framerate   int
	TypingSpeed time.Duration
	CursorBlink bool
}

// DefaultConfig returns the only presentation contract v1 permits.
func DefaultConfig() Config {
	bounds := limits.V1()
	return Config{
		Width:       bounds.Width,
		Height:      bounds.Height,
		FontFamily:  "JetBrains Mono",
		FontSize:    18,
		Theme:       "Catppuccin Mocha",
		Framerate:   30,
		TypingSpeed: 35 * time.Millisecond,
		CursorBlink: false,
	}
}

// outputRoot is the only directory a composed tape may write into.
const outputRoot = "/work/"

// invalidTape builds the single sanitized failure this package may return. The
// field names a bounded schema-owned category and line number only; it never
// carries tape text, a pattern, a command, or an output path.
func invalidTape(category string, line int, err error) error {
	field := category
	if line > 0 {
		field = fmt.Sprintf("%s:%d", category, line)
	}
	return failure.E(failure.InvalidContract, failure.StageTape, field, failure.RuleTapeInvalid, err)
}

// Parse reads a behavior-only tape and returns its validated directives.
func Parse(r io.Reader, bounds limits.Limits) ([]Directive, error) {
	if r == nil {
		return nil, invalidTape("tape", 0, errors.New("tape reader is required"))
	}

	// Read one byte beyond the bound so an oversized tape is detectable
	// without buffering an unbounded amount of input.
	limited := io.LimitReader(r, bounds.TapeBytes+1)
	content, err := io.ReadAll(limited)
	if err != nil {
		return nil, invalidTape("tape", 0, errors.New("tape could not be read"))
	}
	if int64(len(content)) > bounds.TapeBytes {
		return nil, invalidTape("tape", 0, errors.New("tape exceeds its byte bound"))
	}
	if !utf8.Valid(content) {
		return nil, invalidTape("tape", 0, errors.New("tape is not valid UTF-8"))
	}

	var (
		directives []Directive
		typedTotal int
		sleepTotal time.Duration
		waitTotal  time.Duration
	)

	scanner := bufio.NewScanner(strings.NewReader(string(content)))
	scanner.Buffer(make([]byte, 0, 64*1024), int(bounds.TapeBytes)+1)

	for line := 1; scanner.Scan(); line++ {
		text := strings.TrimSuffix(scanner.Text(), "\r")
		trimmed := strings.TrimSpace(text)
		if trimmed == "" || strings.HasPrefix(trimmed, "#") {
			continue
		}

		directive, err := parseDirective(trimmed, line, bounds)
		if err != nil {
			return nil, err
		}

		switch directive.Kind {
		case KindType:
			typedTotal += len(directive.Text)
			if typedTotal > bounds.TypedBytes {
				return nil, invalidTape("typed-total", line, errors.New("typed bytes exceed the cumulative bound"))
			}
		case KindSleep:
			sleepTotal += directive.Duration
			if sleepTotal > bounds.SleepTotal {
				return nil, invalidTape("sleep-total", line, errors.New("sleep exceeds the cumulative bound"))
			}
		case KindWait, KindWaitLine, KindWaitScreen:
			waitTotal += directive.Duration
			if waitTotal > bounds.WaitTotal {
				return nil, invalidTape("wait-total", line, errors.New("wait exceeds the cumulative bound"))
			}
		}

		directives = append(directives, directive)
		if len(directives) > bounds.Directives {
			return nil, invalidTape("directive-count", line, errors.New("tape exceeds its directive bound"))
		}
	}
	if err := scanner.Err(); err != nil {
		return nil, invalidTape("tape", 0, errors.New("tape could not be scanned"))
	}

	return directives, nil
}

// parseDirective validates exactly one non-empty, non-comment line.
func parseDirective(line string, number int, bounds limits.Limits) (Directive, error) {
	name, rest := splitName(line)

	// Reject every timing override before dispatch so no directive can smuggle
	// an @ form through its own argument parser.
	if strings.Contains(name, "@") {
		return Directive{}, invalidTape("timing-override", number, errors.New("per-directive timing is not permitted"))
	}
	if strings.HasPrefix(strings.TrimSpace(rest), "@") {
		return Directive{}, invalidTape("timing-override", number, errors.New("per-directive timing is not permitted"))
	}

	switch {
	case name == string(KindType):
		return parseType(rest, number, bounds)
	case strings.HasPrefix(name, string(KindCtrl)):
		return parseCtrl(name, rest, number)
	case name == string(KindSleep):
		return parseSleep(rest, number, bounds)
	}

	if kind, ok := waitKinds[name]; ok {
		return parseWait(kind, rest, number, bounds)
	}
	if kind := Kind(name); isRepeatableKey(kind) {
		return parseKey(kind, rest, number, bounds)
	}

	return Directive{}, invalidTape("directive", number, errors.New("directive is not permitted by the v1 contract"))
}

// splitName separates the leading directive token from its arguments.
func splitName(line string) (string, string) {
	index := strings.IndexAny(line, " \t")
	if index < 0 {
		return line, ""
	}
	return line[:index], strings.TrimSpace(line[index+1:])
}

func isRepeatableKey(kind Kind) bool {
	_, ok := repeatableKeys[kind]
	return ok
}

// parseType accepts exactly one quoted literal with no escape interpretation,
// matching the VHS lexer, which reads a string verbatim until its delimiter.
func parseType(rest string, number int, bounds limits.Limits) (Directive, error) {
	if rest == "" {
		return Directive{}, invalidTape("type", number, errors.New("Type requires one quoted literal"))
	}

	delimiter := rest[0]
	if delimiter != '"' && delimiter != '\'' && delimiter != '`' {
		return Directive{}, invalidTape("type", number, errors.New("Type requires a quoted literal"))
	}

	closing := strings.IndexByte(rest[1:], delimiter)
	if closing < 0 {
		return Directive{}, invalidTape("type", number, errors.New("Type literal is unterminated"))
	}

	payload := rest[1 : 1+closing]
	if remainder := strings.TrimSpace(rest[2+closing:]); remainder != "" {
		return Directive{}, invalidTape("type", number, errors.New("Type accepts exactly one literal"))
	}
	if len(payload) > bounds.TypedCommandBytes {
		return Directive{}, invalidTape("type", number, errors.New("typed command exceeds its byte bound"))
	}

	return Directive{Kind: KindType, Text: payload, Count: 1, Line: number}, nil
}

// parseCtrl accepts Ctrl+<one printable ASCII character> and nothing else.
func parseCtrl(name, rest string, number int) (Directive, error) {
	if rest != "" {
		return Directive{}, invalidTape("ctrl", number, errors.New("Ctrl accepts no argument"))
	}
	suffix, ok := strings.CutPrefix(name, string(KindCtrl)+"+")
	if !ok {
		return Directive{}, invalidTape("ctrl", number, errors.New("Ctrl requires one character"))
	}
	if len(suffix) != 1 {
		return Directive{}, invalidTape("ctrl", number, errors.New("Ctrl accepts exactly one printable ASCII character"))
	}
	if suffix[0] < 0x20 || suffix[0] > 0x7E {
		return Directive{}, invalidTape("ctrl", number, errors.New("Ctrl character must be printable ASCII"))
	}
	return Directive{Kind: KindCtrl, Text: suffix, Count: 1, Line: number}, nil
}

// parseKey accepts an allowlisted key with an optional base-10 repeat count.
func parseKey(kind Kind, rest string, number int, bounds limits.Limits) (Directive, error) {
	count := 1
	if rest != "" {
		if strings.ContainsAny(rest, " \t") {
			return Directive{}, invalidTape("key", number, errors.New("key accepts at most one count"))
		}
		parsed, err := parseCount(rest, bounds)
		if err != nil {
			return Directive{}, invalidTape("key", number, err)
		}
		count = parsed
	}
	return Directive{Kind: kind, Count: count, Line: number}, nil
}

// parseCount accepts only an unsigned base-10 integer within the repeat bound.
func parseCount(token string, bounds limits.Limits) (int, error) {
	for i := 0; i < len(token); i++ {
		if token[i] < '0' || token[i] > '9' {
			return 0, errors.New("count must be an unsigned base-10 integer")
		}
	}
	value, err := strconv.Atoi(token)
	if err != nil {
		return 0, errors.New("count is not a valid integer")
	}
	if value < 1 || value > bounds.KeyRepeat {
		return 0, errors.New("count is outside its permitted range")
	}
	return value, nil
}

// durationPattern matches one VHS time token: a decimal number with an
// optional ms, s, or m unit. VHS parses exactly one number plus one unit.
var durationPattern = regexp.MustCompile(`^([0-9]+(?:\.[0-9]+)?)(ms|s|m)?$`)

// parseSleep accepts exactly one positive VHS duration token.
func parseSleep(rest string, number int, bounds limits.Limits) (Directive, error) {
	if rest == "" {
		return Directive{}, invalidTape("sleep", number, errors.New("Sleep requires one duration"))
	}
	if strings.ContainsAny(rest, " \t") {
		return Directive{}, invalidTape("sleep", number, errors.New("Sleep accepts exactly one duration"))
	}

	duration, err := parseDurationToken(rest)
	if err != nil {
		return Directive{}, invalidTape("sleep", number, err)
	}
	if duration <= 0 {
		return Directive{}, invalidTape("sleep", number, errors.New("Sleep requires a positive duration"))
	}
	if duration > bounds.Sleep {
		return Directive{}, invalidTape("sleep", number, errors.New("Sleep exceeds its single-directive bound"))
	}
	// The composer emits one VHS time token whose finest unit is a
	// millisecond, so a finer value could not survive a parse/compose round
	// trip. Reject it here rather than silently truncating it later.
	if duration%time.Millisecond != 0 {
		return Directive{}, invalidTape("sleep", number, errors.New("Sleep must be a whole number of milliseconds"))
	}
	return Directive{Kind: KindSleep, Count: 1, Duration: duration, Line: number}, nil
}

// parseDurationToken converts a VHS time token without floating-point
// arithmetic, so a value such as 0.1ms cannot silently truncate to zero.
func parseDurationToken(token string) (time.Duration, error) {
	match := durationPattern.FindStringSubmatch(token)
	if match == nil {
		return 0, errors.New("duration is not a valid VHS time token")
	}

	unit := match[2]
	if unit == "" {
		// VHS treats a missing unit as seconds.
		unit = "s"
	}

	var scale time.Duration
	switch unit {
	case "ms":
		scale = time.Millisecond
	case "s":
		scale = time.Second
	case "m":
		scale = time.Minute
	}

	number := match[1]
	whole, fraction, _ := strings.Cut(number, ".")

	value, err := strconv.ParseInt(whole, 10, 64)
	if err != nil {
		return 0, errors.New("duration magnitude is out of range")
	}
	total := time.Duration(value) * scale

	// Apply the fractional part by exact integer scaling so precision loss is
	// detected rather than rounded away.
	for _, digit := range fraction {
		scale /= 10
		if scale == 0 {
			return 0, errors.New("duration is more precise than one nanosecond")
		}
		total += time.Duration(digit-'0') * scale
	}
	return total, nil
}

// parseWait accepts an optional slash-delimited pattern, compiled only to
// validate its syntax. No match is ever performed here.
func parseWait(kind Kind, rest string, number int, bounds limits.Limits) (Directive, error) {
	directive := Directive{Kind: kind, Count: 1, Duration: bounds.Wait, Line: number}
	if rest == "" {
		return directive, nil
	}
	if rest[0] != '/' {
		return Directive{}, invalidTape("wait", number, errors.New("Wait pattern must be slash-delimited"))
	}

	pattern, remainder, err := cutRegex(rest)
	if err != nil {
		return Directive{}, invalidTape("wait", number, err)
	}
	if strings.TrimSpace(remainder) != "" {
		return Directive{}, invalidTape("wait", number, errors.New("Wait accepts exactly one pattern"))
	}
	if len(pattern) > bounds.WaitPatternBytes {
		return Directive{}, invalidTape("wait", number, errors.New("wait pattern exceeds its byte bound"))
	}
	if _, err := regexp.Compile(pattern); err != nil {
		return Directive{}, invalidTape("wait", number, errors.New("wait pattern is not a valid regular expression"))
	}

	directive.Pattern = pattern
	return directive, nil
}

// cutRegex locates the closing delimiter using the VHS odd-backslash rule: a
// delimiter preceded by an odd number of backslashes is escaped.
func cutRegex(input string) (string, string, error) {
	var backslashes int
	for i := 1; i < len(input); i++ {
		switch input[i] {
		case '\\':
			backslashes++
		case '/':
			if backslashes%2 == 0 {
				return input[1:i], input[i+1:], nil
			}
			backslashes = 0
		default:
			backslashes = 0
		}
	}
	return "", "", errors.New("wait pattern delimiter is unterminated")
}

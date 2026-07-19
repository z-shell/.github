package manifest

import (
	"bytes"
	"errors"
	"fmt"
	"os"
	"path"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
	"time"
	"unicode"
	"unicode/utf8"

	"github.com/santhosh-tekuri/jsonschema/v6"
	"github.com/z-shell/.github/tools/readme-terminal-demo/internal/failure"
	"github.com/z-shell/.github/tools/readme-terminal-demo/internal/limits"
	"go.yaml.in/yaml/v3"
)

const validManifestYAML = `version: 1
scenario: .github/demos/readme.tape
fixtures: .github/demos/fixtures
outputs:
  gif: docs/assets/readme-demo.gif
  png: docs/assets/readme-demo.png
readme:
  path: docs/README.md
  alt: Short description of the behavior shown in the terminal demo.
`

func TestV1LimitsAreImmutableContractValues(t *testing.T) {
	want := limits.Limits{
		ManifestBytes:        16 * 1024,
		YAMLDepth:            16,
		YAMLNodes:            128,
		ScalarBytes:          4 * 1024,
		AltTextBytes:         512,
		TapeBytes:            64 * 1024,
		FixtureFiles:         512,
		FixtureBytes:         16 * 1024 * 1024,
		SingleFixtureBytes:   1024 * 1024,
		SnapshotEntries:      4096,
		SnapshotBytes:        64 * 1024 * 1024,
		SnapshotEntryBytes:   8 * 1024 * 1024,
		SnapshotArchiveBytes: 96 * 1024 * 1024,
		PathBytes:            1024,
		SymlinkTargetBytes:   1024,
		SymlinkDepth:         16,
		DiagnosticBytes:      64 * 1024,
		Directives:           128,
		TypedCommandBytes:    2 * 1024,
		TypedBytes:           16 * 1024,
		WaitPatternBytes:     512,
		KeyRepeat:            32,
		Sleep:                3 * time.Second,
		SleepTotal:           8 * time.Second,
		Wait:                 10 * time.Second,
		WaitTotal:            30 * time.Second,
		Capture:              45 * time.Second,
		Width:                960,
		Height:               540,
		GIFDuration:          12 * time.Second,
		GIFBytes:             5 * 1024 * 1024,
		PNGBytes:             1024 * 1024,
	}
	if got := limits.V1(); !reflect.DeepEqual(got, want) {
		t.Fatalf("V1() = %#v, want %#v", got, want)
	}
	changed := limits.V1()
	changed.Width = 1
	if got := limits.V1().Width; got != want.Width {
		t.Fatalf("fresh V1().Width = %d after caller mutation, want %d", got, want.Width)
	}
}

func TestDecodeAcceptsValidV1Shape(t *testing.T) {
	got, err := Decode(strings.NewReader(validManifestYAML), limits.V1().ManifestBytes)
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}
	if err := Validate(got); err != nil {
		t.Fatalf("Validate() error = %v", err)
	}
	if want := validManifest(); !reflect.DeepEqual(got, want) {
		t.Fatalf("Decode() = %#v, want %#v", got, want)
	}
}

func TestDecodeRejectsUntrustedYAML(t *testing.T) {
	deepValue := strings.Repeat("[", limits.V1().YAMLDepth+1) + "0" + strings.Repeat("]", limits.V1().YAMLDepth+1)
	manyNodes := strings.TrimSuffix(validManifestYAML, "\n") + "\nextra: [" + strings.Repeat("0,", limits.V1().YAMLNodes) + "0]\n"
	oversized := validManifestYAML + strings.Repeat("#", int(limits.V1().ManifestBytes))

	tests := []struct {
		name      string
		input     string
		wantCause string
	}{
		{name: "unknown key", input: validManifestYAML + "unexpected: true\n"},
		{name: "duplicate key", input: validManifestYAML + "version: 1\n"},
		{name: "anchor", input: strings.Replace(validManifestYAML, "version: 1", "version: &version 1", 1), wantCause: "anchor"},
		{
			name: "alias",
			input: strings.Replace(
				strings.Replace(validManifestYAML, "scenario: .github/demos/readme.tape", "scenario: &scenario .github/demos/readme.tape", 1),
				"fixtures: .github/demos/fixtures",
				"fixtures: *scenario",
				1,
			),
			wantCause: "alias",
		},
		{name: "custom tag", input: strings.Replace(validManifestYAML, "version: 1", "version: !contract 1", 1), wantCause: "tag"},
		{name: "multiple documents", input: validManifestYAML + "---\n" + validManifestYAML, wantCause: "multiple YAML documents"},
		{name: "excessive depth", input: validManifestYAML + "extra: " + deepValue + "\n", wantCause: "depth"},
		{name: "excessive nodes", input: manyNodes, wantCause: "node"},
		{
			name:      "oversized multibyte scalar",
			input:     validManifestYAML + "extra: " + strings.Repeat("é", limits.V1().ScalarBytes/2+1) + "\n",
			wantCause: "scalar",
		},
		{name: "oversized input", input: oversized, wantCause: "manifest"},
	}

	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			_, err := Decode(strings.NewReader(test.input), limits.V1().ManifestBytes)
			structured := requireManifestFailure(t, err, failure.InvalidContract)
			if test.wantCause != "" && !strings.Contains(structured.Err.Error(), test.wantCause) {
				t.Fatalf("failure cause = %q, want substring %q", structured.Err, test.wantCause)
			}
		})
	}
}

func TestDecodeRejectsNestedAndWrongShapes(t *testing.T) {
	tests := []struct {
		name      string
		input     string
		wantCause string
	}{
		{name: "empty document", input: ""},
		{name: "empty second document", input: validManifestYAML + "---\n", wantCause: "multiple YAML documents"},
		{name: "non-map document", input: "- version: 1\n"},
		{name: "wrong version type", input: strings.Replace(validManifestYAML, "version: 1", `version: "1"`, 1)},
		{name: "wrong outputs type", input: strings.Replace(validManifestYAML, "outputs:\n  gif: docs/assets/readme-demo.gif\n  png: docs/assets/readme-demo.png", "outputs: []", 1)},
		{name: "nested unknown key", input: strings.Replace(validManifestYAML, "  png: docs/assets/readme-demo.png", "  png: docs/assets/readme-demo.png\n  unexpected: true", 1)},
		{name: "nested duplicate key", input: strings.Replace(validManifestYAML, "  png: docs/assets/readme-demo.png", "  png: docs/assets/readme-demo.png\n  gif: docs/assets/duplicate.gif", 1), wantCause: "duplicate"},
		{name: "binary tag", input: strings.Replace(validManifestYAML, "  alt: Short description of the behavior shown in the terminal demo.", "  alt: !!binary ZGVtbw==", 1), wantCause: "tag"},
		{name: "timestamp tag", input: strings.Replace(validManifestYAML, "  alt: Short description of the behavior shown in the terminal demo.", "  alt: !!timestamp 2026-07-19", 1), wantCause: "tag"},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			_, err := Decode(strings.NewReader(test.input), limits.V1().ManifestBytes)
			structured := requireManifestFailure(t, err, failure.InvalidContract)
			if test.wantCause != "" && !strings.Contains(structured.Err.Error(), test.wantCause) {
				t.Fatalf("failure cause = %q, want substring %q", structured.Err, test.wantCause)
			}
		})
	}

	explicitCore := strings.Replace(validManifestYAML, "version: 1", "version: !!int 1", 1)
	value, err := Decode(strings.NewReader(explicitCore), limits.V1().ManifestBytes)
	if err != nil {
		t.Fatalf("Decode(explicit core tag) error = %v", err)
	}
	if err := Validate(value); err != nil {
		t.Fatalf("Validate(explicit core tag) error = %v", err)
	}
}

func TestDecodeEnforcesExactByteBoundsAndV1Clamp(t *testing.T) {
	if _, err := Decode(strings.NewReader(validManifestYAML), int64(len(validManifestYAML))); err != nil {
		t.Fatalf("Decode(exact caller byte bound) error = %v", err)
	}
	_, err := Decode(strings.NewReader(validManifestYAML), int64(len(validManifestYAML)-1))
	requireManifestFailure(t, err, failure.InvalidContract)

	overV1 := validManifestYAML + strings.Repeat("#", int(limits.V1().ManifestBytes))
	_, err = Decode(strings.NewReader(overV1), limits.V1().ManifestBytes*2)
	structured := requireManifestFailure(t, err, failure.InvalidContract)
	if !strings.Contains(structured.Err.Error(), "manifest") {
		t.Fatalf("failure cause = %q, want manifest V1 byte limit", structured.Err)
	}
}

func TestYAMLPreflightExactBounds(t *testing.T) {
	bounds := limits.V1()

	t.Run("depth", func(t *testing.T) {
		exact := strings.Repeat("[", bounds.YAMLDepth-1) + "0" + strings.Repeat("]", bounds.YAMLDepth-1)
		if err := preflightYAML(parseYAMLNode(t, exact), bounds); err != nil {
			t.Fatalf("preflight exact depth: %v", err)
		}
		tooDeep := "[" + exact + "]"
		if err := preflightYAML(parseYAMLNode(t, tooDeep), bounds); err == nil || !strings.Contains(err.Error(), "depth") {
			t.Fatalf("preflight depth+1 error = %v, want depth limit", err)
		}
	})

	t.Run("nodes", func(t *testing.T) {
		exact := yamlSequence(bounds.YAMLNodes - 2)
		if err := preflightYAML(parseYAMLNode(t, exact), bounds); err != nil {
			t.Fatalf("preflight exact nodes: %v", err)
		}
		tooMany := yamlSequence(bounds.YAMLNodes - 1)
		if err := preflightYAML(parseYAMLNode(t, tooMany), bounds); err == nil || !strings.Contains(err.Error(), "node") {
			t.Fatalf("preflight nodes+1 error = %v, want node limit", err)
		}
	})

	t.Run("multibyte scalar", func(t *testing.T) {
		exact := strings.Repeat("é", bounds.ScalarBytes/2)
		if err := preflightYAML(parseYAMLNode(t, exact), bounds); err != nil {
			t.Fatalf("preflight exact scalar bytes: %v", err)
		}
		tooLarge := exact + "é"
		if err := preflightYAML(parseYAMLNode(t, tooLarge), bounds); err == nil || !strings.Contains(err.Error(), "scalar") {
			t.Fatalf("preflight scalar bytes+2 error = %v, want scalar limit", err)
		}
	})
}

func TestValidateRejectsEveryMissingField(t *testing.T) {
	tests := map[string]func(*Manifest){
		"version":     func(value *Manifest) { value.Version = 0 },
		"scenario":    func(value *Manifest) { value.Scenario = "" },
		"fixtures":    func(value *Manifest) { value.Fixtures = "" },
		"outputs":     func(value *Manifest) { value.Outputs = Outputs{} },
		"outputs.gif": func(value *Manifest) { value.Outputs.GIF = "" },
		"outputs.png": func(value *Manifest) { value.Outputs.PNG = "" },
		"readme":      func(value *Manifest) { value.Readme = Readme{} },
		"readme.path": func(value *Manifest) { value.Readme.Path = "" },
		"readme.alt":  func(value *Manifest) { value.Readme.Alt = "" },
	}

	for name, mutate := range tests {
		t.Run(name, func(t *testing.T) {
			value := validManifest()
			mutate(&value)
			requireManifestFailure(t, Validate(value), failure.InvalidContract)
		})
	}
}

func TestValidateRejectsContractViolations(t *testing.T) {
	tests := []struct {
		name   string
		mutate func(*Manifest)
		class  failure.Class
	}{
		{name: "version other than one", mutate: func(value *Manifest) { value.Version = 2 }, class: failure.InvalidContract},
		{name: "absolute scenario", mutate: func(value *Manifest) { value.Scenario = "/.github/demos/readme.tape" }, class: failure.UnsafePath},
		{name: "scenario dot-dot", mutate: func(value *Manifest) { value.Scenario = ".github/demos/../readme.tape" }, class: failure.UnsafePath},
		{name: "scenario wrong root", mutate: func(value *Manifest) { value.Scenario = "demo/readme.tape" }, class: failure.UnsafePath},
		{name: "scenario wrong extension", mutate: func(value *Manifest) { value.Scenario = ".github/demos/readme.yml" }, class: failure.UnsafePath},
		{name: "scenario empty stem", mutate: func(value *Manifest) { value.Scenario = ".github/demos/.tape" }, class: failure.UnsafePath},
		{name: "fixtures absolute", mutate: func(value *Manifest) { value.Fixtures = "/.github/demos/fixtures" }, class: failure.UnsafePath},
		{name: "fixtures dot-dot", mutate: func(value *Manifest) { value.Fixtures = ".github/demos/../fixtures" }, class: failure.UnsafePath},
		{name: "fixtures wrong root", mutate: func(value *Manifest) { value.Fixtures = "fixtures" }, class: failure.UnsafePath},
		{name: "gif wrong root", mutate: func(value *Manifest) { value.Outputs.GIF = "assets/readme-demo.gif" }, class: failure.UnsafePath},
		{name: "gif wrong extension", mutate: func(value *Manifest) { value.Outputs.GIF = "docs/assets/readme-demo.png" }, class: failure.UnsafePath},
		{name: "gif empty stem", mutate: func(value *Manifest) { value.Outputs.GIF = "docs/assets/.gif" }, class: failure.UnsafePath},
		{name: "png dot-dot", mutate: func(value *Manifest) { value.Outputs.PNG = "docs/assets/../readme-demo.png" }, class: failure.UnsafePath},
		{name: "png wrong root", mutate: func(value *Manifest) { value.Outputs.PNG = "docs/readme-demo.png" }, class: failure.UnsafePath},
		{name: "png wrong extension", mutate: func(value *Manifest) { value.Outputs.PNG = "docs/assets/readme-demo.gif" }, class: failure.UnsafePath},
		{name: "png empty stem", mutate: func(value *Manifest) { value.Outputs.PNG = "docs/assets/.png" }, class: failure.UnsafePath},
		{name: "readme absolute", mutate: func(value *Manifest) { value.Readme.Path = "/README.md" }, class: failure.UnsafePath},
		{name: "readme dot-dot", mutate: func(value *Manifest) { value.Readme.Path = "docs/../README.md" }, class: failure.UnsafePath},
		{name: "readme wrong root", mutate: func(value *Manifest) { value.Readme.Path = "guide/README.md" }, class: failure.UnsafePath},
		{name: "readme wrong extension", mutate: func(value *Manifest) { value.Readme.Path = "docs/README.txt" }, class: failure.UnsafePath},
		{name: "readme empty stem", mutate: func(value *Manifest) { value.Readme.Path = "docs/.md" }, class: failure.UnsafePath},
		{name: "scenario root lookalike", mutate: func(value *Manifest) { value.Scenario = ".github/demos-evil/readme.tape" }, class: failure.UnsafePath},
		{name: "asset root lookalike", mutate: func(value *Manifest) { value.Outputs.GIF = "docs/assets-evil/readme-demo.gif" }, class: failure.UnsafePath},
		{name: "readme root lookalike", mutate: func(value *Manifest) { value.Readme.Path = "docs-evil/README.md" }, class: failure.UnsafePath},
		{name: "non-normal path", mutate: func(value *Manifest) { value.Scenario = ".github//demos/readme.tape" }, class: failure.UnsafePath},
		{name: "backslash path", mutate: func(value *Manifest) { value.Scenario = `.github\demos\readme.tape` }, class: failure.UnsafePath},
		{name: "oversized path", mutate: func(value *Manifest) {
			value.Scenario = ".github/demos/" + strings.Repeat("a", limits.V1().PathBytes) + ".tape"
		}, class: failure.UnsafePath},
		{name: "blank alt text", mutate: func(value *Manifest) { value.Readme.Alt = "   " }, class: failure.InvalidContract},
		{name: "multiline alt text", mutate: func(value *Manifest) { value.Readme.Alt = "first line\nsecond line" }, class: failure.InvalidContract},
		{name: "control character alt text", mutate: func(value *Manifest) { value.Readme.Alt = "demo\u007f" }, class: failure.InvalidContract},
		{name: "oversized alt text", mutate: func(value *Manifest) { value.Readme.Alt = strings.Repeat("a", limits.V1().AltTextBytes+1) }, class: failure.InvalidContract},
	}

	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			value := validManifest()
			test.mutate(&value)
			requireManifestFailure(t, Validate(value), test.class)
		})
	}
}

func TestValidateUsesExactUTF8ByteBounds(t *testing.T) {
	t.Run("path", func(t *testing.T) {
		value := validManifest()
		value.Scenario = byteSizedPath(".github/demos/", ".tape", limits.V1().PathBytes)
		if err := Validate(value); err != nil {
			t.Fatalf("Validate(exact path bytes) error = %v", err)
		}
		value.Scenario = byteSizedPath(".github/demos/", ".tape", limits.V1().PathBytes+1)
		requireManifestFailure(t, Validate(value), failure.UnsafePath)
	})

	t.Run("alt text", func(t *testing.T) {
		value := validManifest()
		value.Readme.Alt = strings.Repeat("é", limits.V1().AltTextBytes/2)
		if err := Validate(value); err != nil {
			t.Fatalf("Validate(exact alt bytes) error = %v", err)
		}
		value.Readme.Alt += "a"
		requireManifestFailure(t, Validate(value), failure.InvalidContract)
	})
}

func TestValidateRejectsEveryAltControlClass(t *testing.T) {
	tests := map[string]string{
		"carriage return":             "demo\rtext",
		"tab":                         "demo\ttext",
		"NUL":                         "demo\x00text",
		"DEL":                         "demo\x7ftext",
		"C1 control":                  "demo\u0085text",
		"Unicode line separator":      "demo\u2028text",
		"Unicode paragraph separator": "demo\u2029text",
	}
	for name, alt := range tests {
		t.Run(name, func(t *testing.T) {
			value := validManifest()
			value.Readme.Alt = alt
			requireManifestFailure(t, Validate(value), failure.InvalidContract)
		})
	}
}

func TestLoadRequiresInputsButNotOutputs(t *testing.T) {
	root := newFileMapReader(t)
	got, err := Load(root, "manifest.yml")
	if err != nil {
		t.Fatalf("Load() error = %v", err)
	}
	if want := validManifest(); !reflect.DeepEqual(got, want) {
		t.Fatalf("Load() = %#v, want %#v", got, want)
	}
	for _, output := range []string{got.Outputs.GIF, got.Outputs.PNG} {
		if contains(root.opened, output) {
			t.Fatalf("Load() opened output %q; opened = %v", output, root.opened)
		}
	}
	for _, file := range root.files {
		if _, err := file.Stat(); !errors.Is(err, os.ErrClosed) {
			t.Fatalf("Reader-returned file remained open: Stat() error = %v", err)
		}
	}
}

func TestLoadRejectsMissingInputs(t *testing.T) {
	for _, missing := range []string{".github/demos/readme.tape", ".github/demos/fixtures", "docs/README.md"} {
		t.Run(missing, func(t *testing.T) {
			root := newFileMapReader(t)
			delete(root.entries, missing)
			_, err := Load(root, "manifest.yml")
			requireManifestFailure(t, err, failure.InvalidContract)
		})
	}
}

func TestLoadPreservesReaderSymlinkEscapeFailure(t *testing.T) {
	root := newFileMapReader(t)
	readerFailure := failure.E(
		failure.UnsafePath,
		failure.StageManifest,
		"scenario",
		failure.RuleManifestInvalid,
		errors.New("symlink escapes repository"),
	)
	root.errs[".github/demos/readme.tape"] = fmt.Errorf("untrusted reader context: %w", readerFailure)
	_, err := Load(root, "manifest.yml")
	requireManifestFailure(t, err, failure.UnsafePath)
	if err != readerFailure {
		t.Fatalf("Load() error = %T %v, want exact sanitized Reader failure", err, err)
	}
}

func TestLoadRejectsWrongInputFileTypesAndClosesThem(t *testing.T) {
	tests := []struct {
		name string
		path string
	}{
		{name: "scenario directory", path: ".github/demos/readme.tape"},
		{name: "fixtures file", path: ".github/demos/fixtures"},
		{name: "README directory", path: "docs/README.md"},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			root := newFileMapReader(t)
			replacement := filepath.Join(t.TempDir(), "wrong-type")
			if test.path == ".github/demos/fixtures" {
				if err := os.WriteFile(replacement, []byte("not a directory"), 0o600); err != nil {
					t.Fatal(err)
				}
			} else if err := os.Mkdir(replacement, 0o700); err != nil {
				t.Fatal(err)
			}
			root.entries[test.path] = replacement
			_, err := Load(root, "manifest.yml")
			requireManifestFailure(t, err, failure.InvalidContract)
			for _, file := range root.files {
				if _, statErr := file.Stat(); !errors.Is(statErr, os.ErrClosed) {
					t.Fatalf("Reader-returned file remained open: Stat() error = %v", statErr)
				}
			}
		})
	}
}

func TestLoadClosesFileReturnedWithError(t *testing.T) {
	root := newFileMapReader(t)
	file, err := os.Open(root.entries[".github/demos/readme.tape"])
	if err != nil {
		t.Fatal(err)
	}
	root.errorFiles[".github/demos/readme.tape"] = file
	root.errs[".github/demos/readme.tape"] = errors.New("reader returned a file and an error")
	_, err = Load(root, "manifest.yml")
	requireManifestFailure(t, err, failure.InvalidContract)
	if _, statErr := file.Stat(); !errors.Is(statErr, os.ErrClosed) {
		t.Fatalf("Reader-returned file remained open: Stat() error = %v", statErr)
	}
}

func TestManifestFailureMessageDoesNotLeakInput(t *testing.T) {
	const secretPath = "/private/secret/manifest.tape"
	value := validManifest()
	value.Scenario = secretPath
	err := Validate(value)
	requireManifestFailure(t, err, failure.UnsafePath)
	if strings.Contains(err.Error(), secretPath) || strings.Contains(err.Error(), "normalized repository-relative") {
		t.Fatalf("public error leaked untrusted detail: %q", err)
	}
}

func TestSchemaParityFixtures(t *testing.T) {
	schema := compileManifestSchema(t)

	suites := []struct {
		dir  string
		want bool
	}{
		{dir: "../../testdata/valid", want: true},
		{dir: "../../testdata/invalid", want: false},
	}
	for _, suite := range suites {
		entries, err := os.ReadDir(suite.dir)
		if err != nil {
			t.Fatalf("read fixtures %s: %v", suite.dir, err)
		}
		if len(entries) == 0 {
			t.Fatalf("fixture directory %s is empty", suite.dir)
		}
		for _, entry := range entries {
			if entry.IsDir() || filepath.Ext(entry.Name()) != ".yml" {
				continue
			}
			name := filepath.Join(suite.dir, entry.Name())
			t.Run(name, func(t *testing.T) {
				data, err := os.ReadFile(name)
				if err != nil {
					t.Fatalf("read fixture: %v", err)
				}

				value, typedErr := Decode(bytes.NewReader(data), limits.V1().ManifestBytes)
				if typedErr == nil {
					typedErr = Validate(value)
				}
				typedAccepted := typedErr == nil

				var document any
				parseErr := yaml.Unmarshal(data, &document)
				var schemaErr error
				if parseErr != nil {
					schemaErr = parseErr
				} else {
					schemaErr = schema.Validate(document)
				}
				schemaAccepted := schemaErr == nil

				if typedAccepted != schemaAccepted {
					t.Fatalf("fixture %s parity mismatch: typed accepted=%t (err=%v), schema accepted=%t (err=%v)", name, typedAccepted, typedErr, schemaAccepted, schemaErr)
				}
				if typedAccepted != suite.want {
					t.Fatalf("fixture %s accepted=%t, want %t; typed err=%v; schema err=%v", name, typedAccepted, suite.want, typedErr, schemaErr)
				}
			})
		}
	}
}

func TestSchemaAndTypedValidationUseUTF8ByteLimits(t *testing.T) {
	schema := compileManifestSchema(t)
	tests := []struct {
		name   string
		mutate func(*Manifest)
		class  failure.Class
	}{
		{
			name: "alt text",
			mutate: func(value *Manifest) {
				value.Readme.Alt = strings.Repeat("é", limits.V1().AltTextBytes/2+1)
			},
			class: failure.InvalidContract,
		},
		{
			name: "path",
			mutate: func(value *Manifest) {
				value.Scenario = ".github/demos/" + strings.Repeat("é", limits.V1().PathBytes/2) + ".tape"
			},
			class: failure.UnsafePath,
		},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			value := validManifest()
			test.mutate(&value)
			requireManifestFailure(t, Validate(value), test.class)
			if err := schema.Validate(manifestDocument(value)); err == nil {
				t.Fatal("schema accepted a value over its UTF-8 byte limit")
			}
		})
	}
}

func compileManifestSchema(t *testing.T) *jsonschema.Schema {
	t.Helper()
	schemaData, err := os.ReadFile("../../manifest.schema.json")
	if err != nil {
		t.Fatalf("read schema: %v", err)
	}
	schemaDocument, err := jsonschema.UnmarshalJSON(bytes.NewReader(schemaData))
	if err != nil {
		t.Fatalf("parse schema: %v", err)
	}
	compiler := jsonschema.NewCompiler()
	compiler.RegisterFormat(&jsonschema.Format{
		Name: "z-shell-path-bytes",
		Validate: func(value any) error {
			text, ok := value.(string)
			if !ok {
				return nil
			}
			if len(text) > limits.V1().PathBytes {
				return errors.New("path exceeds UTF-8 byte limit")
			}
			if !utf8.ValidString(text) || path.IsAbs(text) || text == "." || path.Clean(text) != text {
				return errors.New("path is not normalized repository-relative UTF-8")
			}
			for _, segment := range strings.Split(text, "/") {
				if segment == "" || segment == "." || segment == ".." {
					return errors.New("path contains an unsafe segment")
				}
			}
			for _, character := range text {
				if character == '\\' || unicode.IsControl(character) {
					return errors.New("path contains an unsafe character")
				}
			}
			return nil
		},
	})
	compiler.RegisterFormat(&jsonschema.Format{
		Name: "z-shell-alt-bytes",
		Validate: func(value any) error {
			text, ok := value.(string)
			if !ok {
				return nil
			}
			if len(text) > limits.V1().AltTextBytes {
				return errors.New("alt text exceeds UTF-8 byte limit")
			}
			if !utf8.ValidString(text) || strings.TrimSpace(text) == "" {
				return errors.New("alt text must be non-empty plain UTF-8 text")
			}
			for _, character := range text {
				if unicode.IsControl(character) || character == '\u2028' || character == '\u2029' {
					return errors.New("alt text must be one line without controls")
				}
			}
			return nil
		},
	})
	compiler.AssertFormat()
	if err := compiler.AddResource("manifest.schema.json", schemaDocument); err != nil {
		t.Fatalf("add schema: %v", err)
	}
	schema, err := compiler.Compile("manifest.schema.json")
	if err != nil {
		t.Fatalf("compile schema: %v", err)
	}
	return schema
}

func manifestDocument(value Manifest) map[string]any {
	return map[string]any{
		"version":  value.Version,
		"scenario": value.Scenario,
		"fixtures": value.Fixtures,
		"outputs": map[string]any{
			"gif": value.Outputs.GIF,
			"png": value.Outputs.PNG,
		},
		"readme": map[string]any{
			"path": value.Readme.Path,
			"alt":  value.Readme.Alt,
		},
	}
}

func validManifest() Manifest {
	return Manifest{
		Version:  1,
		Scenario: ".github/demos/readme.tape",
		Fixtures: ".github/demos/fixtures",
		Outputs: Outputs{
			GIF: "docs/assets/readme-demo.gif",
			PNG: "docs/assets/readme-demo.png",
		},
		Readme: Readme{
			Path: "docs/README.md",
			Alt:  "Short description of the behavior shown in the terminal demo.",
		},
	}
}

func requireManifestFailure(t *testing.T, err error, wantClass failure.Class) *failure.Error {
	t.Helper()
	if err == nil {
		t.Fatal("error = nil, want typed manifest failure")
	}
	var structured *failure.Error
	if !errors.As(err, &structured) {
		t.Fatalf("error type = %T, want *failure.Error", err)
	}
	if structured.Class != wantClass {
		t.Fatalf("failure class = %q, want %q", structured.Class, wantClass)
	}
	if structured.Stage != failure.StageManifest {
		t.Fatalf("failure stage = %q, want %q", structured.Stage, failure.StageManifest)
	}
	if structured.Rule != failure.RuleManifestInvalid {
		t.Fatalf("failure rule = %q, want %q", structured.Rule, failure.RuleManifestInvalid)
	}
	wantExit := 2
	if wantClass == failure.UnsafePath {
		wantExit = 3
	}
	if got := failure.ExitCode(err); got != wantExit {
		t.Fatalf("ExitCode() = %d, want %d", got, wantExit)
	}
	return structured
}

type fileMapReader struct {
	entries    map[string]string
	errs       map[string]error
	errorFiles map[string]*os.File
	opened     []string
	files      []*os.File
}

func newFileMapReader(t *testing.T) *fileMapReader {
	t.Helper()
	directory := t.TempDir()
	manifestFile := filepath.Join(directory, "manifest.yml")
	scenarioFile := filepath.Join(directory, "scenario.tape")
	fixturesDirectory := filepath.Join(directory, "fixtures")
	readmeFile := filepath.Join(directory, "README.md")
	if err := os.WriteFile(manifestFile, []byte(validManifestYAML), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(scenarioFile, []byte("Type \"echo demo\"\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := os.Mkdir(fixturesDirectory, 0o700); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(readmeFile, []byte("# Demo\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	return &fileMapReader{
		entries: map[string]string{
			"manifest.yml":              manifestFile,
			".github/demos/readme.tape": scenarioFile,
			".github/demos/fixtures":    fixturesDirectory,
			"docs/README.md":            readmeFile,
		},
		errs:       make(map[string]error),
		errorFiles: make(map[string]*os.File),
	}
}

func (reader *fileMapReader) OpenRead(name string) (*os.File, error) {
	reader.opened = append(reader.opened, name)
	if err := reader.errs[name]; err != nil {
		file := reader.errorFiles[name]
		if file != nil {
			reader.files = append(reader.files, file)
		}
		return file, err
	}
	path, ok := reader.entries[name]
	if !ok {
		return nil, os.ErrNotExist
	}
	file, err := os.Open(path)
	if err == nil {
		reader.files = append(reader.files, file)
	}
	return file, err
}

func contains(values []string, want string) bool {
	for _, value := range values {
		if value == want {
			return true
		}
	}
	return false
}

func parseYAMLNode(t *testing.T, input string) *yaml.Node {
	t.Helper()
	var node yaml.Node
	if err := yaml.NewDecoder(strings.NewReader(input)).Decode(&node); err != nil {
		t.Fatalf("decode YAML test node: %v", err)
	}
	return &node
}

func yamlSequence(items int) string {
	values := make([]string, items)
	for index := range values {
		values[index] = "0"
	}
	return "[" + strings.Join(values, ",") + "]"
}

func byteSizedPath(prefix, extension string, size int) string {
	remaining := size - len(prefix) - len(extension)
	if remaining < 0 {
		panic("path size smaller than fixed components")
	}
	return prefix + strings.Repeat("a", remaining%2) + strings.Repeat("é", remaining/2) + extension
}

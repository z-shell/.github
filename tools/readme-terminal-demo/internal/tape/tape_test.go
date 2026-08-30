package tape

import (
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/z-shell/.github/tools/readme-terminal-demo/internal/failure"
	"github.com/z-shell/.github/tools/readme-terminal-demo/internal/limits"
)

const testOutput = "/work/demo.gif"

func parseString(t *testing.T, input string) ([]Directive, error) {
	t.Helper()
	return Parse(strings.NewReader(input), limits.V1())
}

// assertTapeInvalid proves a rejection uses only the stable sanitized contract
// and never leaks tape source text through the public error string.
func assertTapeInvalid(t *testing.T, err error, secrets ...string) {
	t.Helper()
	if err == nil {
		t.Fatal("expected a failure, got nil")
	}
	if got := failure.Classify(err); got != failure.InvalidContract {
		t.Errorf("class = %q, want %q", got, failure.InvalidContract)
	}
	if got := failure.ExitCode(err); got != 2 {
		t.Errorf("exit code = %d, want 2", got)
	}
	var structured *failure.Error
	if !errors.As(err, &structured) {
		t.Fatalf("error is not a *failure.Error: %v", err)
	}
	if structured.Stage != failure.StageTape {
		t.Errorf("stage = %q, want %q", structured.Stage, failure.StageTape)
	}
	if structured.Rule != failure.RuleTapeInvalid {
		t.Errorf("rule = %q, want %q", structured.Rule, failure.RuleTapeInvalid)
	}
	message := err.Error()
	for _, secret := range secrets {
		if secret != "" && strings.Contains(message, secret) {
			t.Errorf("error message %q leaks source text %q", message, secret)
		}
		if secret != "" && strings.Contains(structured.Field, secret) {
			t.Errorf("error field %q leaks source text %q", structured.Field, secret)
		}
	}
}

func TestParseAcceptsEveryAllowedDirective(t *testing.T) {
	input := strings.Join([]string{
		"# a comment line",
		"   # an indented comment",
		"",
		`Type "ll --git"`,
		"Enter",
		"Tab",
		"Space",
		"Backspace 3",
		"Left",
		"Right 2",
		"Up",
		"Down 4",
		"PageUp",
		"PageDown",
		"ScrollUp 2",
		"ScrollDown",
		"Ctrl+L",
		"Sleep 500ms",
		"Sleep 1s",
		"Wait",
		"Wait+Line",
		`Wait+Screen /\$ $/`,
	}, "\n")

	directives, err := parseString(t, input)
	if err != nil {
		t.Fatalf("Parse returned an unexpected error: %v", err)
	}

	want := []Directive{
		{Kind: KindType, Text: "ll --git", Count: 1, Line: 4},
		{Kind: KindEnter, Count: 1, Line: 5},
		{Kind: KindTab, Count: 1, Line: 6},
		{Kind: KindSpace, Count: 1, Line: 7},
		{Kind: KindBackspace, Count: 3, Line: 8},
		{Kind: KindLeft, Count: 1, Line: 9},
		{Kind: KindRight, Count: 2, Line: 10},
		{Kind: KindUp, Count: 1, Line: 11},
		{Kind: KindDown, Count: 4, Line: 12},
		{Kind: KindPageUp, Count: 1, Line: 13},
		{Kind: KindPageDown, Count: 1, Line: 14},
		{Kind: KindScrollUp, Count: 2, Line: 15},
		{Kind: KindScrollDown, Count: 1, Line: 16},
		{Kind: KindCtrl, Text: "L", Count: 1, Line: 17},
		{Kind: KindSleep, Count: 1, Duration: 500 * time.Millisecond, Line: 18},
		{Kind: KindSleep, Count: 1, Duration: time.Second, Line: 19},
		{Kind: KindWait, Count: 1, Duration: 10 * time.Second, Line: 20},
		{Kind: KindWaitLine, Count: 1, Duration: 10 * time.Second, Line: 21},
		{Kind: KindWaitScreen, Count: 1, Duration: 10 * time.Second, Pattern: `\$ $`, Line: 22},
	}

	if len(directives) != len(want) {
		t.Fatalf("parsed %d directives, want %d", len(directives), len(want))
	}
	for i, expected := range want {
		if directives[i] != expected {
			t.Errorf("directive %d = %+v, want %+v", i, directives[i], expected)
		}
	}
}

func TestParseRejects(t *testing.T) {
	bounds := limits.V1()

	cases := []struct {
		name  string
		input string
	}{
		{"unknown directive", `Frobnicate "x"`},
		{"output directive", `Output "/work/evil.gif"`},
		{"set directive", `Set FontSize 40`},
		{"require directive", `Require "eza"`},
		{"source indirection", `Source "other.tape"`},
		{"lowercase source indirection", `source "other.tape"`},
		{"env directive", `Env KEY "value"`},
		{"screenshot directive", `Screenshot "/work/x.png"`},
		{"copy directive", `Copy "x"`},
		{"paste directive", "Paste"},
		{"hide directive", "Hide"},
		{"show directive", "Show"},
		{"escape directive", "Escape"},
		{"alt modifier", "Alt+x"},
		{"shift modifier", "Shift+x"},
		{"type timing override", `Type@50ms "x"`},
		{"type spaced timing override", `Type @50ms "x"`},
		{"key timing override", "Enter@1s"},
		{"wait timing override", "Wait@5s"},
		{"sleep timing override", "Sleep@1s"},
		{"unquoted type", "Type hello"},
		{"unterminated quote", `Type "hello`},
		{"mismatched quotes", `Type "hello'`},
		{"two type literals", `Type "a" "b"`},
		{"trailing token after type", `Type "a" extra`},
		{"inline comment", "Enter # go"},
		{"trailing token after key", "Enter now"},
		{"negative repeat", "Down -1"},
		{"zero repeat", "Down 0"},
		{"signed repeat", "Down +2"},
		{"fractional repeat", "Down 1.5"},
		{"excessive repeat", "Down 33"},
		{"repeat on ctrl", "Ctrl+L 2"},
		{"ctrl without character", "Ctrl+"},
		{"ctrl bare", "Ctrl"},
		{"ctrl multi character", "Ctrl+Shift"},
		{"ctrl modifier chain", "Ctrl+Alt+p"},
		{"ctrl non ascii", "Ctrl+é"},
		{"sleep without duration", "Sleep"},
		{"sleep zero", "Sleep 0s"},
		{"sleep negative", "Sleep -1s"},
		{"sleep exceeds single bound", "Sleep 4s"},
		{"sleep unknown unit", "Sleep 1h"},
		{"sleep sub millisecond precision", "Sleep 0.0001ms"},
		{"sleep trailing token", "Sleep 1s extra"},
		{"wait malformed regex delimiter", "Wait /unterminated"},
		{"wait invalid regex", `Wait /(unclosed/`},
		{"wait trailing token after regex", "Wait /ok/ extra"},
		{"wait unknown suffix", "Wait+Frame /x/"},
		{"blank directive name only plus", "+"},
		{"leading illegal token", "@"},
	}

	for _, testCase := range cases {
		t.Run(testCase.name, func(t *testing.T) {
			_, err := parseString(t, testCase.input)
			assertTapeInvalid(t, err, testCase.input)
		})
	}

	t.Run("excessive directive count", func(t *testing.T) {
		input := strings.Repeat("Enter\n", bounds.Directives+1)
		_, err := parseString(t, input)
		assertTapeInvalid(t, err)
	})

	t.Run("excessive single typed command bytes", func(t *testing.T) {
		payload := strings.Repeat("a", bounds.TypedCommandBytes+1)
		_, err := parseString(t, `Type "`+payload+`"`)
		assertTapeInvalid(t, err)
	})

	t.Run("excessive total typed bytes", func(t *testing.T) {
		line := `Type "` + strings.Repeat("a", 1024) + `"` + "\n"
		input := strings.Repeat(line, (bounds.TypedBytes/1024)+1)
		_, err := parseString(t, input)
		assertTapeInvalid(t, err)
	})

	t.Run("excessive cumulative sleep", func(t *testing.T) {
		input := strings.Repeat("Sleep 3s\n", 4)
		_, err := parseString(t, input)
		assertTapeInvalid(t, err)
	})

	t.Run("excessive cumulative wait", func(t *testing.T) {
		input := strings.Repeat("Wait\n", 4)
		_, err := parseString(t, input)
		assertTapeInvalid(t, err)
	})

	t.Run("excessive wait pattern bytes", func(t *testing.T) {
		pattern := strings.Repeat("a", bounds.WaitPatternBytes+1)
		_, err := parseString(t, "Wait /"+pattern+"/")
		assertTapeInvalid(t, err)
	})

	t.Run("excessive tape bytes", func(t *testing.T) {
		input := strings.Repeat("# padding comment\n", 8*1024)
		if int64(len(input)) <= bounds.TapeBytes {
			t.Fatalf("test input is not larger than the tape bound")
		}
		_, err := parseString(t, input)
		assertTapeInvalid(t, err)
	})

	t.Run("invalid utf-8", func(t *testing.T) {
		_, err := parseString(t, "Type \"\xff\xfe\"")
		assertTapeInvalid(t, err)
	})
}

func TestParseAcceptsCarriageReturnLineEndings(t *testing.T) {
	directives, err := parseString(t, "Type \"ok\"\r\nEnter\r\n")
	if err != nil {
		t.Fatalf("Parse returned an unexpected error: %v", err)
	}
	if len(directives) != 2 {
		t.Fatalf("parsed %d directives, want 2", len(directives))
	}
	if directives[0].Text != "ok" {
		t.Errorf("typed text = %q, want %q", directives[0].Text, "ok")
	}
}

func TestParseAcceptsFinalLineWithoutNewline(t *testing.T) {
	directives, err := parseString(t, "Enter")
	if err != nil {
		t.Fatalf("Parse returned an unexpected error: %v", err)
	}
	if len(directives) != 1 || directives[0].Kind != KindEnter {
		t.Fatalf("directives = %+v, want a single Enter", directives)
	}
}

func TestParsePreservesQuotedPayloadsVerbatim(t *testing.T) {
	// Quoting only delimits the literal: VHS performs no escape interpretation,
	// so a backslash sequence must survive parsing byte-for-byte.
	directives, err := parseString(t, `Type 'printf "a\nb"'`)
	if err != nil {
		t.Fatalf("Parse returned an unexpected error: %v", err)
	}
	if want := `printf "a\nb"`; directives[0].Text != want {
		t.Errorf("typed text = %q, want %q", directives[0].Text, want)
	}
}

func TestParseTreatsSourceOnlyAsTypedPayload(t *testing.T) {
	directives, err := parseString(t, `Type "source ~/.zshrc"`)
	if err != nil {
		t.Fatalf("Parse returned an unexpected error: %v", err)
	}
	if len(directives) != 1 || directives[0].Kind != KindType {
		t.Fatalf("directives = %+v, want a single Type", directives)
	}
	if want := "source ~/.zshrc"; directives[0].Text != want {
		t.Errorf("typed text = %q, want %q", directives[0].Text, want)
	}
}

func TestComposeGolden(t *testing.T) {
	input := strings.Join([]string{
		"# behavior only",
		`Type "ll"`,
		"Enter",
		"Sleep 1s",
		`Wait+Screen /\$ $/`,
		"Down 3",
		"Ctrl+L",
		"Wait",
		"Wait+Line",
	}, "\n")

	directives, err := parseString(t, input)
	if err != nil {
		t.Fatalf("Parse returned an unexpected error: %v", err)
	}

	got, err := Compose(directives, DefaultConfig(), testOutput)
	if err != nil {
		t.Fatalf("Compose returned an unexpected error: %v", err)
	}

	want := strings.Join([]string{
		`Output "/work/demo.gif"`,
		`Set Shell "zsh"`,
		"Set Width 960",
		"Set Height 540",
		`Set FontFamily "JetBrains Mono"`,
		"Set FontSize 18",
		`Set Theme "Catppuccin Mocha"`,
		"Set Framerate 30",
		"Set TypingSpeed 35ms",
		"Set CursorBlink false",
		`Type "ll"`,
		"Enter",
		"Sleep 1s",
		`Wait+Screen@10s /\$ $/`,
		"Down 3",
		`Ctrl+"L"`,
		"Wait@10s",
		"Wait+Line@10s",
		"",
	}, "\n")

	if string(got) != want {
		t.Errorf("composed tape mismatch\n got:\n%s\nwant:\n%s", got, want)
	}

	// Byte stability: the same inputs must produce identical bytes.
	again, err := Compose(directives, DefaultConfig(), testOutput)
	if err != nil {
		t.Fatalf("second Compose returned an unexpected error: %v", err)
	}
	if string(again) != string(got) {
		t.Error("Compose is not byte-stable across identical invocations")
	}
}

func TestComposeSelectsSafeDelimiterForTypedText(t *testing.T) {
	cases := []struct {
		name string
		text string
		want string
	}{
		{"plain text prefers double quotes", `ll`, `Type "ll"`},
		{"text with double quote falls back to single", `echo "hi"`, `Type 'echo "hi"'`},
		{"text with both quotes falls back to backtick", `echo "a" 'b'`, "Type `echo \"a\" 'b'`"},
	}

	for _, testCase := range cases {
		t.Run(testCase.name, func(t *testing.T) {
			directives := []Directive{{Kind: KindType, Text: testCase.text, Count: 1, Line: 1}}
			got, err := Compose(directives, DefaultConfig(), testOutput)
			if err != nil {
				t.Fatalf("Compose returned an unexpected error: %v", err)
			}
			if !strings.Contains(string(got), testCase.want) {
				t.Errorf("composed tape does not contain %q\ngot:\n%s", testCase.want, got)
			}
		})
	}
}

func TestComposeRejects(t *testing.T) {
	valid := []Directive{{Kind: KindEnter, Count: 1, Line: 1}}

	t.Run("text containing every delimiter", func(t *testing.T) {
		directives := []Directive{{Kind: KindType, Text: "a\"b'c`d", Count: 1, Line: 1}}
		_, err := Compose(directives, DefaultConfig(), testOutput)
		assertTapeInvalid(t, err, "a\"b'c`d")
	})

	t.Run("unknown kind constructed without Parse", func(t *testing.T) {
		directives := []Directive{{Kind: Kind("Screenshot"), Count: 1, Line: 1}}
		_, err := Compose(directives, DefaultConfig(), testOutput)
		assertTapeInvalid(t, err)
	})

	t.Run("empty kind", func(t *testing.T) {
		directives := []Directive{{Count: 1, Line: 1}}
		_, err := Compose(directives, DefaultConfig(), testOutput)
		assertTapeInvalid(t, err)
	})

	t.Run("internally inconsistent key directive", func(t *testing.T) {
		directives := []Directive{{Kind: KindEnter, Text: "unexpected", Count: 1, Line: 1}}
		_, err := Compose(directives, DefaultConfig(), testOutput)
		assertTapeInvalid(t, err)
	})

	t.Run("key repeat out of range", func(t *testing.T) {
		directives := []Directive{{Kind: KindDown, Count: 0, Line: 1}}
		_, err := Compose(directives, DefaultConfig(), testOutput)
		assertTapeInvalid(t, err)
	})

	t.Run("ctrl with multi character text", func(t *testing.T) {
		directives := []Directive{{Kind: KindCtrl, Text: "Shift", Count: 1, Line: 1}}
		_, err := Compose(directives, DefaultConfig(), testOutput)
		assertTapeInvalid(t, err)
	})

	t.Run("sleep with compound duration", func(t *testing.T) {
		// VHS parseTime accepts one number plus one unit; a compound Go
		// duration such as 1m30s cannot be represented.
		directives := []Directive{{Kind: KindSleep, Count: 1, Duration: 90 * time.Second, Line: 1}}
		_, err := Compose(directives, DefaultConfig(), testOutput)
		assertTapeInvalid(t, err)
	})

	t.Run("sleep with sub millisecond duration", func(t *testing.T) {
		directives := []Directive{{Kind: KindSleep, Count: 1, Duration: 500 * time.Microsecond, Line: 1}}
		_, err := Compose(directives, DefaultConfig(), testOutput)
		assertTapeInvalid(t, err)
	})

	t.Run("wait pattern containing the delimiter", func(t *testing.T) {
		directives := []Directive{{Kind: KindWait, Count: 1, Duration: 10 * time.Second, Pattern: "a/b", Line: 1}}
		_, err := Compose(directives, DefaultConfig(), testOutput)
		assertTapeInvalid(t, err)
	})

	outputs := []struct {
		name   string
		output string
	}{
		{"relative output", "work/demo.gif"},
		{"output outside work", "/tmp/demo.gif"},
		{"work root itself", "/work"},
		{"work directory", "/work/"},
		{"traversal", "/work/../etc/demo.gif"},
		{"unclean path", "/work/./demo.gif"},
		{"wrong extension", "/work/demo.png"},
		{"whitespace", "/work/my demo.gif"},
		{"tab", "/work/demo\t.gif"},
		{"control byte", "/work/demo\x00.gif"},
		{"double quote", `/work/de"mo.gif`},
		{"newline", "/work/demo\n.gif"},
		{"empty", ""},
	}
	for _, testCase := range outputs {
		t.Run("output "+testCase.name, func(t *testing.T) {
			_, err := Compose(valid, DefaultConfig(), testCase.output)
			assertTapeInvalid(t, err, testCase.output)
		})
	}

	configs := []struct {
		name   string
		mutate func(*Config)
	}{
		{"width", func(c *Config) { c.Width = 800 }},
		{"height", func(c *Config) { c.Height = 300 }},
		{"font family", func(c *Config) { c.FontFamily = "Comic Sans" }},
		{"font size", func(c *Config) { c.FontSize = 24 }},
		{"theme", func(c *Config) { c.Theme = "Dracula" }},
		{"framerate", func(c *Config) { c.Framerate = 60 }},
		{"typing speed", func(c *Config) { c.TypingSpeed = time.Second }},
		{"cursor blink", func(c *Config) { c.CursorBlink = true }},
	}
	for _, testCase := range configs {
		t.Run("config "+testCase.name, func(t *testing.T) {
			config := DefaultConfig()
			testCase.mutate(&config)
			_, err := Compose(valid, config, testOutput)
			assertTapeInvalid(t, err)
		})
	}
}

// TestComposeCentralDirectivesOriginateOnlyFromConfig proves that no plugin
// text can introduce or alter a central presentation directive.
func TestComposeCentralDirectivesOriginateOnlyFromConfig(t *testing.T) {
	hostile := []Directive{
		{Kind: KindType, Text: `x"` + "\n" + `Set FontSize 96` + "\n" + `Output "/work/evil.gif`, Count: 1, Line: 1},
		{Kind: KindType, Text: `Set Theme "Dracula"`, Count: 1, Line: 2},
	}

	got, err := Compose(hostile, DefaultConfig(), testOutput)
	if err != nil {
		// Rejecting hostile text outright is also a correct outcome.
		assertTapeInvalid(t, err)
		return
	}

	lines := strings.Split(strings.TrimSuffix(string(got), "\n"), "\n")
	for _, prefix := range []string{"Output ", "Set "} {
		var count int
		for _, line := range lines {
			if strings.HasPrefix(line, prefix) {
				count++
			}
		}
		switch prefix {
		case "Output ":
			if count != 1 {
				t.Errorf("found %d Output lines, want exactly 1", count)
			}
		case "Set ":
			if count != composedSetCount {
				t.Errorf("found %d Set lines, want exactly %d", count, composedSetCount)
			}
		}
	}

	if strings.Contains(string(got), "Set FontSize 96") {
		t.Error("plugin text injected a central presentation directive")
	}
	if strings.Contains(string(got), `Output "/work/evil.gif"`) {
		t.Error("plugin text injected an output destination")
	}
}

func TestDefaultConfigMatchesNormativePresentation(t *testing.T) {
	config := DefaultConfig()
	want := Config{
		Width:       960,
		Height:      540,
		FontFamily:  "JetBrains Mono",
		FontSize:    18,
		Theme:       "Catppuccin Mocha",
		Framerate:   30,
		TypingSpeed: 35 * time.Millisecond,
		CursorBlink: false,
	}
	if config != want {
		t.Errorf("DefaultConfig() = %+v, want %+v", config, want)
	}

	bounds := limits.V1()
	if config.Width != bounds.Width || config.Height != bounds.Height {
		t.Errorf("config geometry %dx%d does not match V1 limits %dx%d",
			config.Width, config.Height, bounds.Width, bounds.Height)
	}
}

// TestParseValidTapeFixtures proves the committed valid fixtures parse and
// then compose, so the fixtures track the real contract.
func TestParseValidTapeFixtures(t *testing.T) {
	entries, err := filepath.Glob(filepath.Join("..", "..", "testdata", "valid", "tapes", "*.tape"))
	if err != nil {
		t.Fatalf("glob valid tape fixtures: %v", err)
	}
	if len(entries) == 0 {
		t.Fatal("no valid tape fixtures found")
	}

	for _, entry := range entries {
		t.Run(filepath.Base(entry), func(t *testing.T) {
			file, err := os.Open(entry)
			if err != nil {
				t.Fatalf("open fixture: %v", err)
			}
			defer file.Close()

			directives, err := Parse(file, limits.V1())
			if err != nil {
				t.Fatalf("Parse returned an unexpected error: %v", err)
			}
			if len(directives) == 0 {
				t.Fatal("fixture produced no directives")
			}
			if _, err := Compose(directives, DefaultConfig(), testOutput); err != nil {
				t.Fatalf("Compose returned an unexpected error: %v", err)
			}
		})
	}
}

// TestParseInvalidTapeFixtures proves each committed invalid fixture is
// rejected through the stable sanitized contract.
func TestParseInvalidTapeFixtures(t *testing.T) {
	entries, err := filepath.Glob(filepath.Join("..", "..", "testdata", "invalid", "tapes", "*.tape"))
	if err != nil {
		t.Fatalf("glob invalid tape fixtures: %v", err)
	}
	if len(entries) == 0 {
		t.Fatal("no invalid tape fixtures found")
	}

	for _, entry := range entries {
		t.Run(filepath.Base(entry), func(t *testing.T) {
			file, err := os.Open(entry)
			if err != nil {
				t.Fatalf("open fixture: %v", err)
			}
			defer file.Close()

			_, err = Parse(file, limits.V1())
			assertTapeInvalid(t, err)
		})
	}
}

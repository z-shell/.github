package tape

import (
	"errors"
	"fmt"
	"strconv"
	"strings"
	"time"

	"github.com/z-shell/.github/tools/readme-terminal-demo/internal/limits"
)

// composedSetCount is the exact number of Set directives the trusted header
// emits. The composition test asserts against it so an added or removed
// central control cannot pass unnoticed.
const composedSetCount = 9

// Compose renders a complete, byte-stable VHS tape from validated directives.
//
// Every central control originates from config and output, both typed
// arguments. Directives supply behavior only. Compose independently revalidates
// its inputs so a caller that constructs a Directive without Parse cannot
// bypass the contract.
func Compose(directives []Directive, config Config, output string) ([]byte, error) {
	if err := validateConfig(config); err != nil {
		return nil, err
	}
	if err := validateOutput(output); err != nil {
		return nil, err
	}

	var builder strings.Builder

	// The trusted header, in one fixed order.
	fmt.Fprintf(&builder, "Output %q\n", output)
	builder.WriteString("Set Shell \"zsh\"\n")
	fmt.Fprintf(&builder, "Set Width %d\n", config.Width)
	fmt.Fprintf(&builder, "Set Height %d\n", config.Height)
	fmt.Fprintf(&builder, "Set FontFamily %q\n", config.FontFamily)
	fmt.Fprintf(&builder, "Set FontSize %d\n", config.FontSize)
	fmt.Fprintf(&builder, "Set Theme %q\n", config.Theme)
	fmt.Fprintf(&builder, "Set Framerate %d\n", config.Framerate)
	fmt.Fprintf(&builder, "Set TypingSpeed %s\n", milliseconds(config.TypingSpeed))
	fmt.Fprintf(&builder, "Set CursorBlink %t\n", config.CursorBlink)

	for _, directive := range directives {
		line, err := composeDirective(directive)
		if err != nil {
			return nil, err
		}
		builder.WriteString(line)
		builder.WriteByte('\n')
	}

	return []byte(builder.String()), nil
}

// validateConfig requires the exact approved presentation contract rather than
// accepting arbitrary presentation strings.
func validateConfig(config Config) error {
	if config != DefaultConfig() {
		return invalidTape("config", 0, errors.New("presentation config is not the approved v1 contract"))
	}
	return nil
}

// validateOutput accepts only an absolute, clean, quote-free .gif path strictly
// below /work.
func validateOutput(output string) error {
	if output == "" {
		return invalidTape("output", 0, errors.New("output destination is required"))
	}
	if !strings.HasPrefix(output, outputRoot) {
		return invalidTape("output", 0, errors.New("output must be below the /work root"))
	}

	name := strings.TrimPrefix(output, outputRoot)
	if name == "" {
		return invalidTape("output", 0, errors.New("output must name a file"))
	}
	if !strings.HasSuffix(output, ".gif") {
		return invalidTape("output", 0, errors.New("output must use the .gif extension"))
	}
	for _, segment := range strings.Split(name, "/") {
		if segment == "" || segment == "." || segment == ".." {
			return invalidTape("output", 0, errors.New("output path is not clean"))
		}
	}
	for i := 0; i < len(output); i++ {
		char := output[i]
		if char < 0x20 || char == 0x7F {
			return invalidTape("output", 0, errors.New("output contains a control byte"))
		}
		if char == ' ' || char == '\t' || char == '"' || char == '\'' || char == '`' || char == '\\' {
			return invalidTape("output", 0, errors.New("output contains a character requiring quoting"))
		}
	}
	return nil
}

// composeDirective renders one behavior directive, rejecting any Directive
// whose fields are unknown or internally inconsistent.
func composeDirective(directive Directive) (string, error) {
	switch directive.Kind {
	case KindType:
		if err := requireFields(directive, fieldText); err != nil {
			return "", err
		}
		quoted, err := quoteTyped(directive.Text, directive.Line)
		if err != nil {
			return "", err
		}
		return "Type " + quoted, nil

	case KindCtrl:
		if err := requireFields(directive, fieldText); err != nil {
			return "", err
		}
		if len(directive.Text) != 1 {
			return "", invalidTape("ctrl", directive.Line, errors.New("Ctrl requires exactly one character"))
		}
		if directive.Text[0] < 0x20 || directive.Text[0] > 0x7E {
			return "", invalidTape("ctrl", directive.Line, errors.New("Ctrl character must be printable ASCII"))
		}
		// Quoting the character prevents punctuation from becoming grammar.
		quoted, err := quoteTyped(directive.Text, directive.Line)
		if err != nil {
			return "", err
		}
		return "Ctrl+" + quoted, nil

	case KindSleep:
		if err := requireFields(directive, fieldDuration); err != nil {
			return "", err
		}
		token, err := durationToken(directive.Duration, directive.Line)
		if err != nil {
			return "", err
		}
		return "Sleep " + token, nil

	case KindWait, KindWaitLine, KindWaitScreen:
		if err := requireFields(directive, fieldDuration|fieldPattern); err != nil {
			return "", err
		}
		token, err := durationToken(directive.Duration, directive.Line)
		if err != nil {
			return "", err
		}
		// The fixed timeout keeps Duration authoritative without relying on
		// the VHS default or a global Set WaitTimeout.
		line := string(directive.Kind) + "@" + token
		if directive.Pattern != "" {
			if strings.ContainsAny(directive.Pattern, "/\n\r") {
				return "", invalidTape("wait", directive.Line, errors.New("wait pattern cannot be delimited safely"))
			}
			line += " /" + directive.Pattern + "/"
		}
		return line, nil
	}

	if isRepeatableKey(directive.Kind) {
		if err := requireFields(directive, 0); err != nil {
			return "", err
		}
		if directive.Count == 1 {
			return string(directive.Kind), nil
		}
		return string(directive.Kind) + " " + strconv.Itoa(directive.Count), nil
	}

	return "", invalidTape("directive", directive.Line, errors.New("directive kind is not permitted by the v1 contract"))
}

// field flags name the optional Directive fields a kind may populate.
type field uint8

const (
	fieldText field = 1 << iota
	fieldDuration
	fieldPattern
)

// requireFields rejects a Directive carrying a field its kind does not use, so
// an inconsistent value cannot be silently ignored during composition.
func requireFields(directive Directive, allowed field) error {
	bounds := limits.V1()
	if directive.Count < 1 || directive.Count > bounds.KeyRepeat {
		return invalidTape("directive", directive.Line, errors.New("directive count is outside its permitted range"))
	}
	if allowed&fieldText == 0 && directive.Text != "" {
		return invalidTape("directive", directive.Line, errors.New("directive does not accept text"))
	}
	if allowed&fieldText != 0 && directive.Text == "" {
		return invalidTape("directive", directive.Line, errors.New("directive requires text"))
	}
	if allowed&fieldDuration == 0 && directive.Duration != 0 {
		return invalidTape("directive", directive.Line, errors.New("directive does not accept a duration"))
	}
	if allowed&fieldDuration != 0 && directive.Duration <= 0 {
		return invalidTape("directive", directive.Line, errors.New("directive requires a positive duration"))
	}
	if allowed&fieldPattern == 0 && directive.Pattern != "" {
		return invalidTape("directive", directive.Line, errors.New("directive does not accept a pattern"))
	}
	return nil
}

// quoteTyped selects a delimiter absent from the text. VHS performs no escape
// interpretation, so text containing all three delimiters cannot be expressed.
func quoteTyped(text string, line int) (string, error) {
	if strings.ContainsAny(text, "\n\r") {
		return "", invalidTape("type", line, errors.New("typed text cannot contain a line break"))
	}
	for _, delimiter := range []string{`"`, `'`, "`"} {
		if !strings.Contains(text, delimiter) {
			return delimiter + text + delimiter, nil
		}
	}
	return "", invalidTape("type", line, errors.New("typed text cannot be quoted safely"))
}

// durationToken renders a duration as one VHS time token. VHS accepts exactly
// one number plus one unit, so a compound value such as 1m30s is rejected
// rather than emitted in a form VHS would misparse.
func durationToken(duration time.Duration, line int) (string, error) {
	if duration <= 0 {
		return "", invalidTape("duration", line, errors.New("duration must be positive"))
	}
	switch {
	case duration%time.Minute == 0 && duration < time.Hour:
		return strconv.FormatInt(int64(duration/time.Minute), 10) + "m", nil
	case duration%time.Second == 0 && duration < time.Minute:
		return strconv.FormatInt(int64(duration/time.Second), 10) + "s", nil
	case duration%time.Millisecond == 0 && duration < time.Minute:
		return strconv.FormatInt(int64(duration/time.Millisecond), 10) + "ms", nil
	}
	return "", invalidTape("duration", line, errors.New("duration is not expressible as one VHS time token"))
}

// milliseconds renders a typing speed in the exact normative form.
func milliseconds(duration time.Duration) string {
	return strconv.FormatInt(int64(duration/time.Millisecond), 10) + "ms"
}

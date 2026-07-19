package manifest

import (
	"errors"
	"path"
	"strings"
	"unicode"
	"unicode/utf8"

	"github.com/z-shell/.github/tools/readme-terminal-demo/internal/failure"
	"github.com/z-shell/.github/tools/readme-terminal-demo/internal/limits"
)

// Validate checks only the structural manifest contract; it does not open paths.
func Validate(value Manifest) error {
	if value.Version != 1 {
		return invalidManifest(errors.New("manifest version must be 1"))
	}
	if value.Scenario == "" || value.Fixtures == "" || value.Outputs.GIF == "" ||
		value.Outputs.PNG == "" || value.Readme.Path == "" || value.Readme.Alt == "" {
		return invalidManifest(errors.New("manifest field is required"))
	}

	if err := validateRootedPath("scenario", value.Scenario, ".github/demos", ".tape"); err != nil {
		return err
	}
	if err := validateRootedPath("fixtures", value.Fixtures, ".github/demos", ""); err != nil {
		return err
	}
	if err := validateRootedPath("outputs.gif", value.Outputs.GIF, "docs/assets", ".gif"); err != nil {
		return err
	}
	if err := validateRootedPath("outputs.png", value.Outputs.PNG, "docs/assets", ".png"); err != nil {
		return err
	}
	if err := validateReadmePath(value.Readme.Path); err != nil {
		return err
	}
	if err := validateAltText(value.Readme.Alt); err != nil {
		return err
	}
	return nil
}

func validateRootedPath(field, value, root, extension string) error {
	if err := validateRepositoryPath(field, value); err != nil {
		return err
	}
	if !strings.HasPrefix(value, root+"/") {
		return unsafeManifestPath(field, errors.New("path is outside its required root"))
	}
	if extension != "" {
		if path.Ext(value) != extension || path.Base(value) == extension {
			return unsafeManifestPath(field, errors.New("path has the wrong extension or an empty stem"))
		}
	}
	return nil
}

func validateReadmePath(value string) error {
	if err := validateRepositoryPath("readme.path", value); err != nil {
		return err
	}
	if value == "README.md" {
		return nil
	}
	if !strings.HasPrefix(value, "docs/") {
		return unsafeManifestPath("readme.path", errors.New("README path is outside docs"))
	}
	extension := path.Ext(value)
	if (extension != ".md" && extension != ".markdown") || path.Base(value) == extension {
		return unsafeManifestPath("readme.path", errors.New("README path is not Markdown"))
	}
	return nil
}

func validateRepositoryPath(field, value string) error {
	bounds := limits.V1()
	if len(value) > bounds.PathBytes {
		return unsafeManifestPath(field, errors.New("path exceeds byte limit"))
	}
	if !utf8.ValidString(value) {
		return unsafeManifestPath(field, errors.New("path is not valid UTF-8"))
	}
	if path.IsAbs(value) || value == "." || path.Clean(value) != value {
		return unsafeManifestPath(field, errors.New("path is not normalized repository-relative form"))
	}
	for _, segment := range strings.Split(value, "/") {
		if segment == "" || segment == "." || segment == ".." {
			return unsafeManifestPath(field, errors.New("path contains an unsafe segment"))
		}
	}
	for _, character := range value {
		if character == '\\' || unicode.IsControl(character) {
			return unsafeManifestPath(field, errors.New("path contains an unsafe character"))
		}
	}
	return nil
}

func validateAltText(value string) error {
	if len(value) > limits.V1().AltTextBytes {
		return invalidManifest(errors.New("alt text exceeds byte limit"))
	}
	if !utf8.ValidString(value) {
		return invalidManifest(errors.New("alt text must be valid UTF-8"))
	}
	hasContent := false
	for _, character := range value {
		if unicode.IsControl(character) || character == '\u2028' || character == '\u2029' {
			return invalidManifest(errors.New("alt text must be a single line without control characters"))
		}
		if !unicode.IsSpace(character) &&
			!unicode.In(character, unicode.Zs, unicode.Zl, unicode.Zp, unicode.Cf) {
			hasContent = true
		}
	}
	if !hasContent {
		return invalidManifest(errors.New("alt text must contain visible content"))
	}
	return nil
}

func unsafeManifestPath(field string, err error) error {
	return failure.E(
		failure.UnsafePath,
		failure.StageManifest,
		field,
		failure.RuleManifestInvalid,
		err,
	)
}

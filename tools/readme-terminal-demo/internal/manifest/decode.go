package manifest

import (
	"bytes"
	"errors"
	"fmt"
	"io"
	"os"

	"github.com/z-shell/.github/tools/readme-terminal-demo/internal/failure"
	"github.com/z-shell/.github/tools/readme-terminal-demo/internal/limits"
	"go.yaml.in/yaml/v3"
)

var coreYAMLTags = map[string]struct{}{
	"!!bool":  {},
	"!!float": {},
	"!!int":   {},
	"!!map":   {},
	"!!null":  {},
	"!!seq":   {},
	"!!str":   {},
}

// Decode parses one bounded manifest document through a strict YAML preflight.
func Decode(r io.Reader, maxBytes int64) (Manifest, error) {
	if r == nil {
		return Manifest{}, invalidManifest(errors.New("manifest reader is nil"))
	}
	if maxBytes <= 0 {
		return Manifest{}, invalidManifest(errors.New("manifest byte limit is invalid"))
	}
	contractLimits := limits.V1()
	if maxBytes > contractLimits.ManifestBytes {
		maxBytes = contractLimits.ManifestBytes
	}

	data, err := io.ReadAll(io.LimitReader(r, maxBytes+1))
	if err != nil {
		return Manifest{}, invalidManifest(fmt.Errorf("read manifest: %w", err))
	}
	if int64(len(data)) > maxBytes {
		return Manifest{}, invalidManifest(errors.New("manifest exceeds byte limit"))
	}

	decoder := yaml.NewDecoder(bytes.NewReader(data))
	var document yaml.Node
	if err := decoder.Decode(&document); err != nil {
		return Manifest{}, invalidManifest(fmt.Errorf("decode YAML node: %w", err))
	}
	if len(document.Content) == 0 {
		return Manifest{}, invalidManifest(errors.New("manifest document is empty"))
	}
	var extra yaml.Node
	if err := decoder.Decode(&extra); err == nil {
		return Manifest{}, invalidManifest(errors.New("multiple YAML documents are not allowed"))
	} else if !errors.Is(err, io.EOF) {
		return Manifest{}, invalidManifest(fmt.Errorf("decode trailing YAML document: %w", err))
	}

	if err := preflightYAML(&document, contractLimits); err != nil {
		return Manifest{}, invalidManifest(err)
	}
	if err := validateManifestNodeShape(&document); err != nil {
		return Manifest{}, invalidManifest(err)
	}

	typed := yaml.NewDecoder(bytes.NewReader(data))
	typed.KnownFields(true)
	var value Manifest
	if err := typed.Decode(&value); err != nil {
		return Manifest{}, invalidManifest(fmt.Errorf("decode typed manifest: %w", err))
	}
	return value, nil
}

// Load opens, decodes, validates, and proves all declared repository inputs exist.
func Load(root Reader, manifestPath string) (Manifest, error) {
	if root == nil {
		return Manifest{}, invalidManifest(errors.New("repository reader is nil"))
	}
	manifestFile, err := openInput(root, "manifest", manifestPath, false)
	if err != nil {
		return Manifest{}, err
	}
	value, decodeErr := Decode(manifestFile, limits.V1().ManifestBytes)
	closeErr := manifestFile.Close()
	if decodeErr != nil {
		return Manifest{}, decodeErr
	}
	if closeErr != nil {
		return Manifest{}, invalidManifest(fmt.Errorf("close manifest: %w", closeErr))
	}
	if err := Validate(value); err != nil {
		return Manifest{}, err
	}

	inputs := []struct {
		field     string
		path      string
		directory bool
	}{
		{field: "scenario", path: value.Scenario},
		{field: "fixtures", path: value.Fixtures, directory: true},
		{field: "readme.path", path: value.Readme.Path},
	}
	for _, input := range inputs {
		file, err := openInput(root, input.field, input.path, input.directory)
		if err != nil {
			return Manifest{}, err
		}
		if err := file.Close(); err != nil {
			return Manifest{}, invalidManifest(fmt.Errorf("close %s input: %w", input.field, err))
		}
	}
	return value, nil
}

func preflightYAML(document *yaml.Node, bounds limits.Limits) error {
	if hasYAMLAlias(document) {
		return errors.New("YAML aliases are not allowed")
	}
	nodes := 0
	return inspectYAMLNode(document, 0, &nodes, bounds)
}

func hasYAMLAlias(node *yaml.Node) bool {
	if node == nil {
		return false
	}
	if node.Kind == yaml.AliasNode || node.Alias != nil {
		return true
	}
	for _, child := range node.Content {
		if hasYAMLAlias(child) {
			return true
		}
	}
	return false
}

func inspectYAMLNode(node *yaml.Node, depth int, nodes *int, bounds limits.Limits) error {
	if node == nil {
		return errors.New("nil YAML node")
	}
	*nodes++
	if *nodes > bounds.YAMLNodes {
		return errors.New("YAML node limit exceeded")
	}
	if node.Kind != yaml.DocumentNode {
		depth++
		if depth > bounds.YAMLDepth {
			return errors.New("YAML depth limit exceeded")
		}
	}
	if node.Anchor != "" {
		return errors.New("YAML anchors are not allowed")
	}
	if node.Kind != yaml.DocumentNode {
		if _, ok := coreYAMLTags[node.ShortTag()]; !ok {
			return errors.New("custom YAML tags are not allowed")
		}
	}
	if node.Kind == yaml.ScalarNode && len(node.Value) > bounds.ScalarBytes {
		return errors.New("YAML scalar byte limit exceeded")
	}
	if node.Kind == yaml.MappingNode {
		if len(node.Content)%2 != 0 {
			return errors.New("invalid YAML mapping")
		}
		keys := make(map[string]struct{}, len(node.Content)/2)
		for index := 0; index < len(node.Content); index += 2 {
			key := node.Content[index]
			if key.Kind != yaml.ScalarNode {
				return errors.New("YAML mapping keys must be scalars")
			}
			if key.ShortTag() != "!!str" {
				return errors.New("manifest mapping keys must be strings")
			}
			fingerprint := key.ShortTag() + "\x00" + key.Value
			if _, exists := keys[fingerprint]; exists {
				return errors.New("duplicate YAML mapping key")
			}
			keys[fingerprint] = struct{}{}
		}
	}
	for _, child := range node.Content {
		if err := inspectYAMLNode(child, depth, nodes, bounds); err != nil {
			return err
		}
	}
	return nil
}

func validateManifestNodeShape(document *yaml.Node) error {
	if document.Kind != yaml.DocumentNode || len(document.Content) != 1 {
		return errors.New("manifest must contain one YAML document node")
	}
	root := document.Content[0]
	if err := requireMappingNode(root, "manifest root"); err != nil {
		return err
	}
	for index := 0; index < len(root.Content); index += 2 {
		key, value := root.Content[index], root.Content[index+1]
		switch key.Value {
		case "version":
			if err := requireScalarTag(value, "!!int", "version"); err != nil {
				return err
			}
		case "scenario", "fixtures":
			if err := requireScalarTag(value, "!!str", key.Value); err != nil {
				return err
			}
		case "outputs":
			if err := validateStringMapping(value, "outputs", "gif", "png"); err != nil {
				return err
			}
		case "readme":
			if err := validateStringMapping(value, "readme", "path", "alt"); err != nil {
				return err
			}
		}
	}
	return nil
}

func validateStringMapping(node *yaml.Node, name string, stringFields ...string) error {
	if err := requireMappingNode(node, name); err != nil {
		return err
	}
	wanted := make(map[string]struct{}, len(stringFields))
	for _, field := range stringFields {
		wanted[field] = struct{}{}
	}
	for index := 0; index < len(node.Content); index += 2 {
		key, value := node.Content[index], node.Content[index+1]
		if _, ok := wanted[key.Value]; !ok {
			continue
		}
		if err := requireScalarTag(value, "!!str", name+"."+key.Value); err != nil {
			return err
		}
	}
	return nil
}

func requireMappingNode(node *yaml.Node, name string) error {
	if node.Kind != yaml.MappingNode || node.ShortTag() != "!!map" {
		return fmt.Errorf("%s must be a mapping", name)
	}
	return nil
}

func requireScalarTag(node *yaml.Node, tag, name string) error {
	if node.Kind != yaml.ScalarNode || node.ShortTag() != tag {
		return fmt.Errorf("%s must use YAML tag %s", name, tag)
	}
	return nil
}

func openInput(root Reader, field, path string, wantDirectory bool) (*os.File, error) {
	file, err := root.OpenRead(path)
	if err != nil {
		if file != nil {
			_ = file.Close()
		}
		var structured *failure.Error
		if errors.As(err, &structured) {
			return nil, structured
		}
		return nil, invalidManifest(fmt.Errorf("open %s input: %w", field, err))
	}
	if file == nil {
		return nil, invalidManifest(fmt.Errorf("open %s input: nil file", field))
	}
	info, err := file.Stat()
	if err != nil {
		_ = file.Close()
		return nil, invalidManifest(fmt.Errorf("inspect %s input: %w", field, err))
	}
	if wantDirectory != info.IsDir() || (!wantDirectory && !info.Mode().IsRegular()) {
		_ = file.Close()
		return nil, invalidManifest(fmt.Errorf("%s input has the wrong file type", field))
	}
	return file, nil
}

func invalidManifest(err error) error {
	return failure.E(
		failure.InvalidContract,
		failure.StageManifest,
		"",
		failure.RuleManifestInvalid,
		err,
	)
}

package manifest

import "os"

// Manifest is the complete README terminal-demo contract.
type Manifest struct {
	Version  int     `yaml:"version"`
	Scenario string  `yaml:"scenario"`
	Fixtures string  `yaml:"fixtures"`
	Outputs  Outputs `yaml:"outputs"`
	Readme   Readme  `yaml:"readme"`
}

// Outputs names the two repository-owned media assets.
type Outputs struct {
	GIF string `yaml:"gif"`
	PNG string `yaml:"png"`
}

// Readme identifies the document and accessible animation description.
type Readme struct {
	Path string `yaml:"path"`
	Alt  string `yaml:"alt"`
}

// Reader opens repository paths through the caller's containment boundary.
type Reader interface {
	OpenRead(string) (*os.File, error)
}

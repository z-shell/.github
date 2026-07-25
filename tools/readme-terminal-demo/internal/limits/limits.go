// Package limits owns immutable, versioned resource bounds for the renderer.
package limits

import "time"

// Limits contains every resource bound fixed by a manifest contract version.
type Limits struct {
	ManifestBytes        int64
	YAMLDepth            int
	YAMLNodes            int
	ScalarBytes          int
	AltTextBytes         int
	TapeBytes            int64
	FixtureFiles         int
	FixtureBytes         int64
	SingleFixtureBytes   int64
	SnapshotEntries      int
	SnapshotBytes        int64
	SnapshotEntryBytes   int64
	SnapshotArchiveBytes int64
	PathBytes            int
	SymlinkTargetBytes   int
	SymlinkDepth         int
	DiagnosticBytes      int
	Directives           int
	TypedCommandBytes    int
	TypedBytes           int
	WaitPatternBytes     int
	KeyRepeat            int
	Sleep                time.Duration
	SleepTotal           time.Duration
	Wait                 time.Duration
	WaitTotal            time.Duration
	Capture              time.Duration
	Width                int
	Height               int
	GIFDuration          time.Duration
	GIFBytes             int64
	PNGBytes             int64
}

// V1 returns the fixed resource bounds for manifest contract version 1.
func V1() Limits {
	return Limits{
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
}

// Package failure defines the renderer's stable, sanitized failure contract.
package failure

import (
	"errors"
	"fmt"
)

// Class is a stable public failure category.
type Class string

const (
	InvalidContract     Class = "invalid-contract"
	UnsafePath          Class = "unsafe-path"
	RendererUnavailable Class = "renderer-unavailable"
	ExecutionFailed     Class = "execution-failed"
	Nondeterministic    Class = "nondeterministic"
	AssetDrift          Class = "asset-drift"
	ReadmeContract      Class = "readme-contract"
)

// Stage is a stable renderer lifecycle stage.
type Stage string

const (
	StageInput      Stage = "input"
	StageCheckout   Stage = "checkout"
	StagePull       Stage = "pull"
	StageProvenance Stage = "provenance"
	StageSnapshot   Stage = "snapshot"
	StageSource     Stage = "source"
	StageManifest   Stage = "manifest"
	StageTape       Stage = "tape"
	StageFixture    Stage = "fixture"
	StageReadme     Stage = "readme"
	StageCapture    Stage = "capture"
	StageMedia      Stage = "media"
	StageStability  Stage = "stability"
	StageCompare    Stage = "compare"
	StagePromotion  Stage = "promotion"
	StageRuntime    Stage = "runtime"
	StagePreRelease Stage = "pre-release"
	StageComplete   Stage = "complete"
)

var stages = [...]Stage{
	StageInput, StageCheckout, StagePull, StageProvenance, StageSnapshot,
	StageSource, StageManifest, StageTape, StageFixture, StageReadme,
	StageCapture, StageMedia, StageStability, StageCompare, StagePromotion,
	StageRuntime, StagePreRelease, StageComplete,
}

// Stages returns the complete stable stage vocabulary in lifecycle order.
func Stages() []Stage {
	result := make([]Stage, len(stages))
	copy(result, stages[:])
	return result
}

// Rule is a stable machine-readable failure rule.
type Rule string

const (
	RuleInputRepository     Rule = "input.repository"
	RuleInputRef            Rule = "input.ref"
	RuleInputManifestPath   Rule = "input.manifest-path"
	RuleCheckoutUnavailable Rule = "checkout.unavailable"
	RuleCheckoutHead        Rule = "checkout.head"
	RuleCheckoutClean       Rule = "checkout.clean"
	RulePullUnavailable     Rule = "pull.unavailable"
	RuleProvenanceInvalid   Rule = "provenance.invalid"
	RuleSnapshotUnavailable Rule = "snapshot.unavailable"
	RuleSnapshotMember      Rule = "snapshot.member"
	RuleSourceMutated       Rule = "source.mutated"
	RuleManifestInvalid     Rule = "manifest.invalid"
	RuleTapeInvalid         Rule = "tape.invalid"
	RuleFixtureInvalid      Rule = "fixture.invalid"
	RuleReadmeInvalid       Rule = "readme.invalid"
	RuleRuntimeUnavailable  Rule = "runtime.unavailable"
	RuleCaptureFailed       Rule = "capture.failed"
	RuleCaptureTimeout      Rule = "capture.timeout"
	RuleMediaFailed         Rule = "media.failed"
	RuleMediaInvalid        Rule = "media.invalid"
	RuleStabilityMismatch   Rule = "stability.mismatch"
	RuleAssetsMissing       Rule = "assets.missing"
	RuleAssetsDrift         Rule = "assets.drift"
	RulePromotionFailed     Rule = "promotion.failed"
	RulePreReleaseDisabled  Rule = "pre-release.disabled"
)

var rules = [...]Rule{
	RuleInputRepository, RuleInputRef, RuleInputManifestPath,
	RuleCheckoutUnavailable, RuleCheckoutHead, RuleCheckoutClean,
	RulePullUnavailable, RuleProvenanceInvalid, RuleSnapshotUnavailable,
	RuleSnapshotMember, RuleSourceMutated, RuleManifestInvalid,
	RuleTapeInvalid, RuleFixtureInvalid, RuleReadmeInvalid,
	RuleRuntimeUnavailable, RuleCaptureFailed, RuleCaptureTimeout,
	RuleMediaFailed, RuleMediaInvalid, RuleStabilityMismatch,
	RuleAssetsMissing, RuleAssetsDrift, RulePromotionFailed,
	RulePreReleaseDisabled,
}

// Rules returns the complete stable rule vocabulary in contract order.
func Rules() []Rule {
	result := make([]Rule, len(rules))
	copy(result, rules[:])
	return result
}

// Error carries only bounded structured context alongside an unlogged cause.
type Error struct {
	Class Class
	Stage Stage
	Field string
	Rule  Rule
	Err   error
}

// E constructs a structured failure.
func E(class Class, stage Stage, field string, rule Rule, err error) error {
	return &Error{Class: class, Stage: stage, Field: field, Rule: rule, Err: err}
}

// Error formats only stable contract values; the wrapped cause and field are
// deliberately excluded because they can originate in untrusted input.
func (e *Error) Error() string {
	return fmt.Sprintf("%s: %s (%s)", e.Class, e.Stage, e.Rule)
}

// Unwrap exposes the cause for programmatic inspection without logging it.
func (e *Error) Unwrap() error {
	return e.Err
}

// Classify returns the stable class of err, or the zero value when unexpected.
func Classify(err error) Class {
	var structured *Error
	if errors.As(err, &structured) {
		return structured.Class
	}
	return ""
}

// ExitCode maps stable failure classes to their public process status.
func ExitCode(err error) int {
	switch Classify(err) {
	case InvalidContract:
		return 2
	case UnsafePath:
		return 3
	case RendererUnavailable:
		return 4
	case ExecutionFailed:
		return 5
	case Nondeterministic:
		return 6
	case AssetDrift:
		return 7
	case ReadmeContract:
		return 8
	default:
		return 1
	}
}

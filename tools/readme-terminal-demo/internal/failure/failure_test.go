package failure

import (
	"errors"
	"reflect"
	"strings"
	"testing"
)

func TestStableClassesAndExitCodes(t *testing.T) {
	t.Parallel()

	tests := []struct {
		class Class
		value string
		code  int
	}{
		{InvalidContract, "invalid-contract", 2},
		{UnsafePath, "unsafe-path", 3},
		{RendererUnavailable, "renderer-unavailable", 4},
		{ExecutionFailed, "execution-failed", 5},
		{Nondeterministic, "nondeterministic", 6},
		{AssetDrift, "asset-drift", 7},
		{ReadmeContract, "readme-contract", 8},
	}

	for _, test := range tests {
		test := test
		t.Run(test.value, func(t *testing.T) {
			t.Parallel()

			err := E(test.class, StageRuntime, "", RuleRuntimeUnavailable, errors.New("private detail"))
			if got := string(test.class); got != test.value {
				t.Fatalf("class value = %q, want %q", got, test.value)
			}
			if got := Classify(err); got != test.class {
				t.Fatalf("Classify() = %q, want %q", got, test.class)
			}
			if got := ExitCode(err); got != test.code {
				t.Fatalf("ExitCode() = %d, want %d", got, test.code)
			}
		})
	}
}

func TestUnexpectedErrorsUseExitOne(t *testing.T) {
	t.Parallel()

	if got := ExitCode(errors.New("unexpected")); got != 1 {
		t.Fatalf("ExitCode() = %d, want 1", got)
	}
}

func TestErrorPreservesStructuredContextWithoutLeakingCause(t *testing.T) {
	t.Parallel()

	cause := errors.New("token=must-not-appear")
	err := E(RendererUnavailable, StageRuntime, "fixtures[2].source", RuleRuntimeUnavailable, cause)

	var structured *Error
	if !errors.As(err, &structured) {
		t.Fatalf("errors.As() did not find *Error in %T", err)
	}
	if structured.Class != RendererUnavailable || structured.Stage != StageRuntime || structured.Field != "fixtures[2].source" || structured.Rule != RuleRuntimeUnavailable {
		t.Fatalf("structured error = %#v", structured)
	}
	if !errors.Is(err, cause) {
		t.Fatal("structured error does not unwrap to its cause")
	}
	if strings.Contains(err.Error(), "must-not-appear") {
		t.Fatalf("Error() leaked wrapped cause: %q", err.Error())
	}
}

func TestStableStageValues(t *testing.T) {
	t.Parallel()

	want := []Stage{
		StageInput, StageCheckout, StagePull, StageProvenance, StageSnapshot,
		StageSource, StageManifest, StageTape, StageFixture, StageReadme,
		StageCapture, StageMedia, StageStability, StageCompare, StagePromotion,
		StageRuntime, StagePreRelease, StageComplete,
	}
	if got := Stages(); !reflect.DeepEqual(got, want) {
		t.Fatalf("Stages() = %#v, want %#v", got, want)
	}
	if StageComplete != "complete" {
		t.Fatalf("StageComplete = %q, want complete", StageComplete)
	}
}

func TestStableRuleValues(t *testing.T) {
	t.Parallel()

	want := []Rule{
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
	if got := Rules(); !reflect.DeepEqual(got, want) {
		t.Fatalf("Rules() = %#v, want %#v", got, want)
	}
}

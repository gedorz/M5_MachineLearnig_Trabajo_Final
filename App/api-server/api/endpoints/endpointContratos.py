from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, root_validator


class DerivedFeatureDefinition(BaseModel):
	name: str = Field(..., min_length=2, max_length=120)
	expression: str = Field(..., min_length=1, description="Expresión pandas eval usando columnas existentes")
	description: str | None = Field(default=None, max_length=500)


class FeatureJustification(BaseModel):
	feature: str = Field(..., min_length=1)
	reason: str = Field(..., min_length=3, max_length=1000)


class FeatureProfileItem(BaseModel):
	name: str
	dtype: str
	null_count: int
	null_ratio: float
	unique_count: int
	is_numeric: bool
	suggested_role: Literal["target", "candidate", "exclude_leakage"]


class FeatureProfileResponse(BaseModel):
	dataset_id: int
	version_id: int
	row_count: int
	target_candidates: list[str]
	leakage_suggestions: list[str]
	features: list[FeatureProfileItem]


class FeaturePlanCreateRequest(BaseModel):
	dataset_id: int
	version_id: int | None = None
	target_col: str = Field(default="is_canceled")
	include_features: list[str] = Field(default_factory=list)
	exclude_features: list[str] = Field(default_factory=list)
	derived_features: list[DerivedFeatureDefinition] = Field(default_factory=list)
	justifications: list[FeatureJustification] = Field(default_factory=list)
	notes: str | None = Field(default=None, max_length=3000)

	@root_validator(skip_on_failure=True)
	def validate_feature_overlap(cls, values):
		include_features = set(values.get("include_features") or [])
		exclude_features = set(values.get("exclude_features") or [])
		overlap = sorted(include_features & exclude_features)
		if overlap:
			raise ValueError(
				f"No se permite solapamiento entre include_features y exclude_features: {overlap}"
			)
		return values


class FeaturePlanSummary(BaseModel):
	target_col: str
	selected_features: list[str]
	excluded_features: list[str]
	derived_features: list[str]
	leakage_columns_present: list[str]


class FeaturePlanCreateResponse(BaseModel):
	plan_id: int
	operation_name: str
	dataset_id: int
	version_id: int
	summary: FeaturePlanSummary


class FeaturePlanGetResponse(BaseModel):
	plan_id: int
	dataset_id: int
	version_id: int
	created_at: str
	plan: FeaturePlanCreateRequest
	summary: FeaturePlanSummary


class FeaturePlanApplyRequest(BaseModel):
	dataset_id: int
	version_id: int | None = None
	plan_id: int | None = None
	plan: FeaturePlanCreateRequest | None = None


class FeaturePlanApplyResponse(BaseModel):
	dataset_id: int
	source_version_id: int
	new_version_id: int
	new_version_number: int
	storage_path: str
	summary: FeaturePlanSummary


class FeaturePlanAutoMLRequest(BaseModel):
	dataset_id: int
	version_id: int | None = None
	plan_id: int | None = None
	plan: FeaturePlanCreateRequest | None = None
	test_size: float = Field(default=0.2, ge=0.05, le=0.5)
	random_state: int = 42
	primary_metric: str = Field(default="roc_auc")
	optimize_hyperparams: bool = True


package com.travel.planner.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

// ---- Auth ----
@Serializable
data class RegisterRequest(
    val phone: String,
    val password: String,
    val nickname: String? = null,
)

@Serializable
data class LoginRequest(
    @SerialName("method") val method: String = "password",
    val phone: String,
    val password: String? = null,
    val code: String? = null,
)

@Serializable
data class SmsCodeRequest(val phone: String)

@Serializable
data class SmsCodeResult(
    @SerialName("expires_in") val expiresIn: Int = 60,
    @SerialName("retry_after") val retryAfter: Int = 60,
    @SerialName("need_captcha") val needCaptcha: Boolean = false,
)

@Serializable
data class RefreshTokenRequest(@SerialName("refresh_token") val refreshToken: String)

@Serializable
data class UpdateProfileRequest(
    val nickname: String? = null,
    @SerialName("avatar_url") val avatarUrl: String? = null,
)

// ---- Plan ----
@Serializable
data class ShareRequest(
    @SerialName("expire_in") val expireIn: Int? = null,
    val password: String? = null,
)

// ---- Trip ----
@Serializable
data class StartTripRequest(@SerialName("plan_id") val planId: String)

@Serializable
data class StatusUpdateRequest(val status: String)

@Serializable
data class CheckinRequest(
    @SerialName("poi_type") val poiType: String,
    @SerialName("poi_name") val poiName: String,
    @SerialName("poi_id") val poiId: String? = null,
    val lat: Double? = null,
    val lng: Double? = null,
    val photos: List<Map<String, String>> = emptyList(),
    @SerialName("planned_at") val plannedAt: String? = null,
    @SerialName("actual_at") val actualAt: String? = null,
    @SerialName("planned_cost") val plannedCost: Double? = null,
    @SerialName("actual_cost") val actualCost: Double? = null,
    val rating: Int? = null,
    val note: String? = null,
)

@Serializable
data class ExpenseRequest(
    val category: String,
    val amount: Double,
    @SerialName("planned_amount") val plannedAmount: Double? = null,
    val note: String? = null,
    @SerialName("spent_at") val spentAt: String? = null,
    @SerialName("checkin_id") val checkinId: String? = null,
)

@Serializable
data class AdjustmentDetectRequest(
    @SerialName("trigger_type") val triggerType: String,
    @SerialName("trigger_detail") val triggerDetail: Map<String, String>? = null,
    val destination: String = "",
)

// ---- Travelogue ----
@Serializable
data class TravelogueGenerateRequest(
    @SerialName("trip_id") val tripId: String,
    val style: String = "diary",
)

@Serializable
data class TravelogueUpdateRequest(
    val title: String? = null,
    val content: String? = null,
    @SerialName("cover_url") val coverUrl: String? = null,
    val status: String? = null,
)

@Serializable
data class MaterialGenerateRequest(@SerialName("trip_id") val tripId: String)

@Serializable
data class MaterialListResult(val materials: List<com.travel.planner.domain.model.SocialMaterial>)

@Serializable
data class FavoriteRequest(@SerialName("is_favorite") val isFavorite: Boolean = true)

@Serializable
data class ShareCreateRequest(
    @SerialName("target_type") val targetType: String,
    @SerialName("target_id") val targetId: String,
    val password: String? = null,
    @SerialName("expire_hours") val expireHours: Int? = null,
)

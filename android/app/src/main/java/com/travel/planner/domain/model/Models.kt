package com.travel.planner.domain.model

import kotlinx.serialization.Serializable

// ---- Auth ----
@Serializable
data class TokenResult(
    val accessToken: String,
    val refreshToken: String,
    val expiresIn: Int = 7200,
)

@Serializable
data class UserProfile(
    val id: String = "",
    val phone: String? = null,
    val nickname: String? = null,
    val avatarUrl: String? = null,
)

// ---- Plan ----
@Serializable
data class PlanSummary(
    val id: String,
    val title: String = "",
    val destination: String = "",
    val startDate: String? = null,
    val endDate: String? = null,
    val days: Int = 0,
    val estimatedCost: Double = 0.0,
    val status: String = "",
    val isFavorite: Boolean = false,
    val createdAt: String? = null,
)

@Serializable
data class PlanDetail(
    val id: String,
    val title: String = "",
    val destination: String = "",
    val startDate: String? = null,
    val endDate: String? = null,
    val days: Int = 0,
    val peopleCount: Int = 1,
    val totalBudget: Double = 0.0,
    val estimatedCost: Double = 0.0,
    val status: String = "",
    val dailyItinerary: List<DayPlan> = emptyList(),
)

@Serializable
data class DayPlan(
    val day: Int,
    val attractions: List<AttractionItem> = emptyList(),
    val meals: List<MealItem> = emptyList(),
)

@Serializable
data class AttractionItem(
    val name: String,
    val reason: String = "",
    val durationHours: Double = 2.0,
    val price: Double = 0.0,
    val latitude: Double? = null,
    val longitude: Double? = null,
)

@Serializable
data class MealItem(
    val meal: String,
    val restaurant: String,
    val reason: String = "",
    val avgPrice: Double = 0.0,
)

// ---- Trip (V2.0) ----
@Serializable
data class Trip(
    val id: String,
    val planId: String = "",
    val status: String = "active",
    val currentDay: Int = 1,
    val totalPois: Int = 0,
    val checkedIn: Int = 0,
    val budgetTotal: Double = 0.0,
    val budgetSpent: Double = 0.0,
    val budgetRemain: Double = 0.0,
)

@Serializable
data class TripProgress(
    val tripId: String,
    val status: String = "",
    val currentDay: Int = 1,
    val progressPct: Double = 0.0,
    val checkedIn: Int = 0,
    val totalPois: Int = 0,
    val budgetTotal: Double = 0.0,
    val budgetSpent: Double = 0.0,
    val budgetRemain: Double = 0.0,
    val timeDeltaTotalMin: Int = 0,
)

@Serializable
data class Checkin(
    val id: String = "",
    val tripId: String = "",
    val poiType: String = "",
    val poiName: String = "",
    val photos: List<PhotoMeta> = emptyList(),
    val rating: Int? = null,
    val note: String? = null,
    val plannedCost: Double? = null,
    val actualCost: Double? = null,
    val plannedAt: String? = null,
    val actualAt: String? = null,
    val timeDeltaMin: Int = 0,
    val createdAt: String? = null,
)

@Serializable
data class PhotoMeta(
    val url: String,
    val aiCaption: String? = null,
    val aiTags: List<String>? = null,
    val qualityScore: Double? = null,
)

@Serializable
data class Adjustment(
    val id: String,
    val tripId: String = "",
    val triggerType: String = "",
    val reason: String? = null,
    val status: String = "pending",
)

// ---- Travelogue (V2.0) ----
@Serializable
data class Travelogue(
    val id: String,
    val tripId: String = "",
    val title: String? = null,
    val content: String? = null,
    val coverUrl: String? = null,
    val photos: List<String> = emptyList(),
    val totalDays: Int? = null,
    val totalPois: Int? = null,
    val totalCost: Double? = null,
    val status: String = "draft",
)

@Serializable
data class SocialMaterial(
    val id: String,
    val tripId: String = "",
    val type: String = "",
    val title: String? = null,
    val content: String? = null,
    val hashtags: List<String> = emptyList(),
    val locationTag: String? = null,
    val images: List<MaterialImage> = emptyList(),
    val layout: String? = null,
    val overlayData: Map<String, String>? = null,
    val sourceDay: Int? = null,
    val isFavorite: Boolean = false,
)

@Serializable
data class MaterialImage(
    val url: String,
    val caption: String? = null,
    val order: Int = 0,
    val isCover: Boolean = false,
)

@Serializable
data class ShareData(
    val shareCode: String,
    val shareUrl: String,
    val viewCount: Int = 0,
)

// ---- SSE Event ----
@Serializable
data class SseEvent(
    val event: String,
    val data: Map<String, kotlinx.serialization.json.JsonElement>? = null,
)

// ---- API Response Wrapper ----
@Serializable
data class ApiResponse<T>(
    val code: Int = 0,
    val message: String = "",
    val data: T? = null,
)

@Serializable
data class PaginatedData<T>(
    val list: List<T> = emptyList(),
    val total: Int = 0,
    val page: Int = 1,
    val pageSize: Int = 20,
)

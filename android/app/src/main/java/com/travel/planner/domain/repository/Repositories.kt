package com.travel.planner.domain.repository

import com.travel.planner.data.remote.dto.*
import com.travel.planner.domain.model.*
import kotlinx.coroutines.flow.Flow

interface AuthRepository {
    suspend fun login(phone: String, password: String): Result<TokenResult>
    suspend fun loginWithSms(phone: String, code: String): Result<TokenResult>
    suspend fun register(phone: String, password: String, nickname: String?): Result<TokenResult>
    suspend fun refreshToken(refreshToken: String): Result<TokenResult>
    suspend fun logout()
    suspend fun isLoggedIn(): Boolean
    fun getAccessToken(): Flow<String>
}

interface ChatRepository {
    fun connectStream(sessionId: String, lastEventId: String? = null): Flow<com.travel.planner.data.remote.sse.SseEvent>
    fun cancelStream()
    suspend fun createSession(title: String?): Result<String>
    suspend fun sendMessage(sessionId: String, content: String)
    suspend fun getMessages(sessionId: String, page: Int = 1): Result<List<Message>>
}

data class Message(
    val id: String = "",
    val role: String = "",
    val content: String = "",
    val createdAt: String? = null,
)

interface PlanRepository {
    suspend fun listPlans(page: Int = 1, status: String? = null): Result<PaginatedData<PlanSummary>>
    suspend fun getPlan(planId: String): Result<PlanDetail>
    suspend fun deletePlan(planId: String): Result<Unit>
    suspend fun exportPlan(planId: String, format: String): Result<ByteArray>
    suspend fun sharePlan(planId: String, password: String?, expireHours: Int?): Result<ShareData>
    suspend fun toggleFavorite(planId: String): Result<Unit>
    suspend fun startTrip(planId: String): Result<Trip>
}

interface TripRepository {
    suspend fun listTrips(page: Int = 1, status: String? = null): Result<PaginatedData<Trip>>
    suspend fun getTrip(tripId: String): Result<Trip>
    suspend fun updateStatus(tripId: String, status: String): Result<Trip>
    suspend fun getProgress(tripId: String): Result<TripProgress>
    suspend fun checkin(tripId: String, request: CheckinRequest): Result<Checkin>
    suspend fun listCheckins(tripId: String): Result<PaginatedData<Checkin>>
    suspend fun addExpense(tripId: String, request: ExpenseRequest): Result<Unit>
    suspend fun detectAnomalies(tripId: String, request: AdjustmentDetectRequest): Result<Adjustment>
    suspend fun listAdjustments(tripId: String): Result<PaginatedData<Adjustment>>
    suspend fun acceptAdjustment(tripId: String, adjId: String): Result<Adjustment>
    suspend fun rejectAdjustment(tripId: String, adjId: String): Result<Adjustment>
}

interface TravelogueRepository {
    suspend fun generate(tripId: String, style: String): Result<Travelogue>
    suspend fun listTravelogues(page: Int = 1): Result<PaginatedData<Travelogue>>
    suspend fun getTravelogue(id: String): Result<Travelogue>
    suspend fun updateTravelogue(id: String, request: TravelogueUpdateRequest): Result<Travelogue>
    suspend fun publish(id: String): Result<Travelogue>
    suspend fun generateMaterials(tripId: String): Result<List<SocialMaterial>>
    suspend fun listMaterials(tripId: String): Result<List<SocialMaterial>>
    suspend fun favoriteMaterial(materialId: String, isFavorite: Boolean): Result<SocialMaterial>
    suspend fun createShare(targetType: String, targetId: String, password: String?, expireHours: Int?): Result<ShareData>
    suspend fun getShareByCode(code: String): Result<ShareData>
}

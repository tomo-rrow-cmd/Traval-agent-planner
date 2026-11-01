package com.travel.planner.data.remote.api

import com.travel.planner.data.remote.dto.*
import com.travel.planner.domain.model.*
import retrofit2.http.*

interface TripApi {

    @POST("trips")
    suspend fun startTrip(@Body request: StartTripRequest): ApiResponse<Trip>

    @GET("trips")
    suspend fun listTrips(
        @Query("page") page: Int = 1,
        @Query("page_size") pageSize: Int = 20,
        @Query("status") status: String? = null,
    ): ApiResponse<PaginatedData<Trip>>

    @GET("trips/{tripId}")
    suspend fun getTrip(@Path("tripId") tripId: String): ApiResponse<Trip>

    @PATCH("trips/{tripId}")
    suspend fun updateTripStatus(
        @Path("tripId") tripId: String,
        @Body request: StatusUpdateRequest,
    ): ApiResponse<Trip>

    @GET("trips/{tripId}/progress")
    suspend fun getProgress(@Path("tripId") tripId: String): ApiResponse<TripProgress>

    @POST("trips/{tripId}/checkins")
    suspend fun checkin(
        @Path("tripId") tripId: String,
        @Body request: CheckinRequest,
    ): ApiResponse<Checkin>

    @GET("trips/{tripId}/checkins")
    suspend fun listCheckins(
        @Path("tripId") tripId: String,
        @Query("page") page: Int = 1,
        @Query("page_size") pageSize: Int = 100,
    ): ApiResponse<PaginatedData<Checkin>>

    @POST("trips/{tripId}/expenses")
    suspend fun addExpense(
        @Path("tripId") tripId: String,
        @Body request: ExpenseRequest,
    ): ApiResponse<Unit>

    @GET("trips/{tripId}/expenses")
    suspend fun listExpenses(
        @Path("tripId") tripId: String,
        @Query("category") category: String? = null,
    ): ApiResponse<List<Unit>>

    @POST("trips/{tripId}/adjustments/detect")
    suspend fun detectAnomalies(
        @Path("tripId") tripId: String,
        @Body request: AdjustmentDetectRequest,
    ): ApiResponse<Adjustment>

    @GET("trips/{tripId}/adjustments")
    suspend fun listAdjustments(
        @Path("tripId") tripId: String,
        @Query("status") status: String? = null,
    ): ApiResponse<PaginatedData<Adjustment>>

    @POST("trips/{tripId}/adjustments/{adjId}/accept")
    suspend fun acceptAdjustment(
        @Path("tripId") tripId: String,
        @Path("adjId") adjId: String,
    ): ApiResponse<Adjustment>

    @POST("trips/{tripId}/adjustments/{adjId}/reject")
    suspend fun rejectAdjustment(
        @Path("tripId") tripId: String,
        @Path("adjId") adjId: String,
    ): ApiResponse<Adjustment>

    @GET("trips/{tripId}/reminder")
    suspend fun getReminder(@Path("tripId") tripId: String): ApiResponse<Map<String, String>>
}

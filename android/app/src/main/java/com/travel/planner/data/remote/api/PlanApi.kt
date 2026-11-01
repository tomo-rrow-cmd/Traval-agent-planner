package com.travel.planner.data.remote.api

import com.travel.planner.data.remote.dto.ShareRequest
import com.travel.planner.domain.model.ApiResponse
import com.travel.planner.domain.model.PaginatedData
import com.travel.planner.domain.model.PlanDetail
import com.travel.planner.domain.model.PlanSummary
import com.travel.planner.domain.model.ShareData
import retrofit2.http.*

interface PlanApi {

    @GET("plans")
    suspend fun listPlans(
        @Query("page") page: Int = 1,
        @Query("page_size") pageSize: Int = 20,
        @Query("status") status: String? = null,
    ): ApiResponse<PaginatedData<PlanSummary>>

    @GET("plans/{planId}")
    suspend fun getPlan(@Path("planId") planId: String): ApiResponse<PlanDetail>

    @DELETE("plans/{planId}")
    suspend fun deletePlan(@Path("planId") planId: String): ApiResponse<Unit>

    @POST("plans/{planId}/exports")
    suspend fun exportPlan(
        @Path("planId") planId: String,
        @Query("format") format: String,
    ): okhttp3.ResponseBody

    @POST("plans/{planId}/shares")
    suspend fun sharePlan(
        @Path("planId") planId: String,
        @Body request: ShareRequest,
    ): ApiResponse<com.travel.planner.domain.model.ShareData>

    @POST("plans/{planId}/favorites")
    suspend fun toggleFavorite(@Path("planId") planId: String): ApiResponse<Unit>
}

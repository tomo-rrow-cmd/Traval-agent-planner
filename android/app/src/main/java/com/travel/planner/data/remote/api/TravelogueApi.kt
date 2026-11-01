package com.travel.planner.data.remote.api

import com.travel.planner.data.remote.dto.*
import com.travel.planner.domain.model.*
import retrofit2.http.*

interface TravelogueApi {

    @POST("travelogues")
    suspend fun generateTravelogue(@Body request: TravelogueGenerateRequest): ApiResponse<Travelogue>

    @GET("travelogues")
    suspend fun listTravelogues(
        @Query("page") page: Int = 1,
        @Query("page_size") pageSize: Int = 20,
        @Query("status") status: String? = null,
    ): ApiResponse<PaginatedData<Travelogue>>

    @GET("travelogues/{id}")
    suspend fun getTravelogue(@Path("id") id: String): ApiResponse<Travelogue>

    @PATCH("travelogues/{id}")
    suspend fun updateTravelogue(
        @Path("id") id: String,
        @Body request: TravelogueUpdateRequest,
    ): ApiResponse<Travelogue>

    @POST("travelogues/{id}/publish")
    suspend fun publishTravelogue(@Path("id") id: String): ApiResponse<Travelogue>

    @POST("travelogues/materials/generate")
    suspend fun generateMaterials(@Body request: MaterialGenerateRequest): ApiResponse<MaterialListResult>

    @GET("travelogues/materials")
    suspend fun listMaterials(
        @Query("trip_id") tripId: String,
        @Query("type") type: String? = null,
    ): ApiResponse<List<SocialMaterial>>

    @POST("travelogues/materials/{materialId}/favorite")
    suspend fun favoriteMaterial(
        @Path("materialId") materialId: String,
        @Body request: FavoriteRequest,
    ): ApiResponse<SocialMaterial>

    @POST("travelogues/shares")
    suspend fun createShare(@Body request: ShareCreateRequest): ApiResponse<ShareData>

    @GET("travelogues/shares/{code}")
    suspend fun getShareByCode(@Path("code") code: String): ApiResponse<ShareData>
}

package com.travel.planner.data.repository

import com.travel.planner.data.remote.api.PlanApi
import com.travel.planner.data.remote.api.TripApi
import com.travel.planner.data.remote.dto.ShareRequest
import com.travel.planner.data.remote.dto.StartTripRequest
import com.travel.planner.domain.model.*
import com.travel.planner.domain.repository.PlanRepository
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class PlanRepositoryImpl @Inject constructor(
    private val planApi: PlanApi,
    private val tripApi: TripApi,
) : PlanRepository {

    override suspend fun listPlans(page: Int, status: String?): Result<PaginatedData<PlanSummary>> = runCatching {
        planApi.listPlans(page = page, status = status).data ?: PaginatedData()
    }

    override suspend fun getPlan(planId: String): Result<PlanDetail> = runCatching {
        planApi.getPlan(planId).data ?: throw Exception("Plan not found")
    }

    override suspend fun deletePlan(planId: String): Result<Unit> = runCatching {
        planApi.deletePlan(planId)
    }

    override suspend fun exportPlan(planId: String, format: String): Result<ByteArray> = runCatching {
        planApi.exportPlan(planId, format).bytes()
    }

    override suspend fun sharePlan(planId: String, password: String?, expireHours: Int?): Result<ShareData> = runCatching {
        planApi.sharePlan(planId, ShareRequest(expireIn = expireHours, password = password)).data
            ?: throw Exception("Share failed")
    }

    override suspend fun toggleFavorite(planId: String): Result<Unit> = runCatching {
        planApi.toggleFavorite(planId)
    }

    override suspend fun startTrip(planId: String): Result<Trip> = runCatching {
        tripApi.startTrip(StartTripRequest(planId)).data ?: throw Exception("Failed to start trip")
    }
}

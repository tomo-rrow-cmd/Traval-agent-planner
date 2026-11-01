package com.travel.planner.data.repository

import com.travel.planner.data.remote.api.TripApi
import com.travel.planner.data.remote.dto.*
import com.travel.planner.domain.model.*
import com.travel.planner.domain.repository.TripRepository
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class TripRepositoryImpl @Inject constructor(
    private val tripApi: TripApi,
) : TripRepository {

    override suspend fun listTrips(page: Int, status: String?): Result<PaginatedData<Trip>> = runCatching {
        tripApi.listTrips(page = page, status = status).data ?: PaginatedData()
    }

    override suspend fun getTrip(tripId: String): Result<Trip> = runCatching {
        tripApi.getTrip(tripId).data ?: throw Exception("Trip not found")
    }

    override suspend fun updateStatus(tripId: String, status: String): Result<Trip> = runCatching {
        tripApi.updateTripStatus(tripId, StatusUpdateRequest(status)).data
            ?: throw Exception("Failed to update status")
    }

    override suspend fun getProgress(tripId: String): Result<TripProgress> = runCatching {
        tripApi.getProgress(tripId).data ?: throw Exception("Progress not found")
    }

    override suspend fun checkin(tripId: String, request: CheckinRequest): Result<Checkin> = runCatching {
        tripApi.checkin(tripId, request).data ?: throw Exception("Checkin failed")
    }

    override suspend fun listCheckins(tripId: String): Result<PaginatedData<Checkin>> = runCatching {
        tripApi.listCheckins(tripId).data ?: PaginatedData()
    }

    override suspend fun addExpense(tripId: String, request: ExpenseRequest): Result<Unit> = runCatching {
        tripApi.addExpense(tripId, request)
    }

    override suspend fun detectAnomalies(tripId: String, request: AdjustmentDetectRequest): Result<Adjustment> = runCatching {
        tripApi.detectAnomalies(tripId, request).data ?: throw Exception("Detection failed")
    }

    override suspend fun listAdjustments(tripId: String): Result<PaginatedData<Adjustment>> = runCatching {
        tripApi.listAdjustments(tripId).data ?: PaginatedData()
    }

    override suspend fun acceptAdjustment(tripId: String, adjId: String): Result<Adjustment> = runCatching {
        tripApi.acceptAdjustment(tripId, adjId).data ?: throw Exception("Failed to accept")
    }

    override suspend fun rejectAdjustment(tripId: String, adjId: String): Result<Adjustment> = runCatching {
        tripApi.rejectAdjustment(tripId, adjId).data ?: throw Exception("Failed to reject")
    }
}

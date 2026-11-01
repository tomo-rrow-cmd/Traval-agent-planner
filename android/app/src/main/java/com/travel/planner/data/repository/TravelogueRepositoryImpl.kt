package com.travel.planner.data.repository

import com.travel.planner.data.remote.api.TravelogueApi
import com.travel.planner.data.remote.dto.*
import com.travel.planner.domain.model.*
import com.travel.planner.domain.repository.TravelogueRepository
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class TravelogueRepositoryImpl @Inject constructor(
    private val api: TravelogueApi,
) : TravelogueRepository {

    override suspend fun generate(tripId: String, style: String): Result<Travelogue> = runCatching {
        api.generateTravelogue(TravelogueGenerateRequest(tripId, style)).data
            ?: throw Exception("Generation failed")
    }

    override suspend fun listTravelogues(page: Int): Result<PaginatedData<Travelogue>> = runCatching {
        api.listTravelogues(page = page).data ?: PaginatedData()
    }

    override suspend fun getTravelogue(id: String): Result<Travelogue> = runCatching {
        api.getTravelogue(id).data ?: throw Exception("Travelogue not found")
    }

    override suspend fun updateTravelogue(id: String, request: TravelogueUpdateRequest): Result<Travelogue> = runCatching {
        api.updateTravelogue(id, request).data ?: throw Exception("Update failed")
    }

    override suspend fun publish(id: String): Result<Travelogue> = runCatching {
        api.publishTravelogue(id).data ?: throw Exception("Publish failed")
    }

    override suspend fun generateMaterials(tripId: String): Result<List<SocialMaterial>> = runCatching {
        api.generateMaterials(MaterialGenerateRequest(tripId)).data?.materials
            ?: throw Exception("Material generation failed")
    }

    override suspend fun listMaterials(tripId: String): Result<List<SocialMaterial>> = runCatching {
        api.listMaterials(tripId).data ?: emptyList()
    }

    override suspend fun favoriteMaterial(materialId: String, isFavorite: Boolean): Result<SocialMaterial> = runCatching {
        api.favoriteMaterial(materialId, FavoriteRequest(isFavorite)).data
            ?: throw Exception("Favorite failed")
    }

    override suspend fun createShare(targetType: String, targetId: String, password: String?, expireHours: Int?): Result<ShareData> = runCatching {
        api.createShare(ShareCreateRequest(targetType, targetId, password, expireHours)).data
            ?: throw Exception("Share failed")
    }

    override suspend fun getShareByCode(code: String): Result<ShareData> = runCatching {
        api.getShareByCode(code).data ?: throw Exception("Share not found")
    }
}

package com.travel.planner.presentation.navigation

import kotlinx.serialization.Serializable

// ---- Auth ----
@Serializable object LoginRoute
@Serializable object RegisterRoute

// ---- Home ----
@Serializable object HomeRoute

// ---- Chat ----
@Serializable object ChatRoute
@Serializable data class ChatSessionRoute(val sessionId: String)

// ---- Plans ----
@Serializable object PlanListRoute
@Serializable data class PlanDetailRoute(val planId: String)

// ---- Trip (V2.0) ----
@Serializable data class TripExecuteRoute(val tripId: String)
@Serializable data class CheckInRoute(val tripId: String)

// ---- Travelogue (V2.0) ----
@Serializable data class TravelogueRoute(val travelogueId: String)
@Serializable data class MaterialListRoute(val tripId: String)
@Serializable data class SharedViewRoute(val shareCode: String)

// ---- Profile ----
@Serializable object ProfileRoute

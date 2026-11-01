package com.travel.planner.presentation.navigation

import androidx.compose.runtime.Composable
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.toRoute
import com.travel.planner.presentation.screens.auth.LoginScreen
import com.travel.planner.presentation.screens.auth.RegisterScreen
import com.travel.planner.presentation.screens.home.HomeScreen
import com.travel.planner.presentation.screens.chat.ChatScreen
import com.travel.planner.presentation.screens.chat.ChatSessionScreen
import com.travel.planner.presentation.screens.plan.PlanDetailScreen
import com.travel.planner.presentation.screens.plan.PlanListScreen
import com.travel.planner.presentation.screens.trip.TripExecuteScreen
import com.travel.planner.presentation.screens.trip.CheckInScreen
import com.travel.planner.presentation.screens.travelogue.TravelogueScreen
import com.travel.planner.presentation.screens.travelogue.MaterialListScreen
import com.travel.planner.presentation.screens.ProfileScreen

@Composable
fun AppNavigation(navController: NavHostController = rememberNavController()) {
    NavHost(
        navController = navController,
        startDestination = LoginRoute,
    ) {
        // Auth
        composable<LoginRoute> {
            LoginScreen(
                onLoginSuccess = {
                    navController.navigate(HomeRoute) {
                        popUpTo(LoginRoute) { inclusive = true }
                    }
                },
                onNavigateToRegister = { navController.navigate(RegisterRoute) },
            )
        }
        composable<RegisterRoute> {
            RegisterScreen(
                onRegisterSuccess = {
                    navController.navigate(HomeRoute) {
                        popUpTo(LoginRoute) { inclusive = true }
                    }
                },
                onNavigateBack = { navController.popBackStack() },
            )
        }

        // Home
        composable<HomeRoute> {
            HomeScreen(
                onNavigateToChat = { navController.navigate(ChatRoute) },
                onNavigateToPlanDetail = { planId -> navController.navigate(PlanDetailRoute(planId)) },
                onNavigateToTrip = { tripId -> navController.navigate(TripExecuteRoute(tripId)) },
                onNavigateToTravelogue = { id -> navController.navigate(TravelogueRoute(id)) },
                onNavigateToProfile = { navController.navigate(ProfileRoute) },
                onLogout = {
                    navController.navigate(LoginRoute) {
                        popUpTo(LoginRoute) { inclusive = true }
                    }
                },
            )
        }

        // Chat
        composable<ChatRoute> {
            ChatScreen(
                onNavigateToSession = { sessionId ->
                    navController.navigate(ChatSessionRoute(sessionId))
                },
                onNavigateBack = { navController.popBackStack() },
            )
        }
        composable<ChatSessionRoute> { backStackEntry ->
            val route = backStackEntry.toRoute<ChatSessionRoute>()
            ChatSessionScreen(
                sessionId = route.sessionId,
                onPlanCreated = { planId ->
                    navController.navigate(PlanDetailRoute(planId))
                },
                onNavigateBack = { navController.popBackStack() },
            )
        }

        // Plans
        composable<PlanListRoute> {
            PlanListScreen(
                onNavigateToPlan = { planId -> navController.navigate(PlanDetailRoute(planId)) },
                onNavigateBack = { navController.popBackStack() },
            )
        }
        composable<PlanDetailRoute> { backStackEntry ->
            val route = backStackEntry.toRoute<PlanDetailRoute>()
            PlanDetailScreen(
                planId = route.planId,
                onStartTrip = { tripId -> navController.navigate(TripExecuteRoute(tripId)) },
                onNavigateBack = { navController.popBackStack() },
            )
        }

        // Trip (V2.0)
        composable<TripExecuteRoute> { backStackEntry ->
            val route = backStackEntry.toRoute<TripExecuteRoute>()
            TripExecuteScreen(
                tripId = route.tripId,
                onNavigateToCheckIn = { navController.navigate(CheckInRoute(route.tripId)) },
                onNavigateToMaterials = { navController.navigate(MaterialListRoute(route.tripId)) },
                onNavigateBack = { navController.popBackStack() },
            )
        }
        composable<CheckInRoute> { backStackEntry ->
            val route = backStackEntry.toRoute<CheckInRoute>()
            CheckInScreen(
                tripId = route.tripId,
                onCheckInComplete = { navController.popBackStack() },
            )
        }

        // Travelogue (V2.0)
        composable<TravelogueRoute> { backStackEntry ->
            val route = backStackEntry.toRoute<TravelogueRoute>()
            TravelogueScreen(
                travelogueId = route.travelogueId,
                onNavigateBack = { navController.popBackStack() },
            )
        }
        composable<MaterialListRoute> { backStackEntry ->
            val route = backStackEntry.toRoute<MaterialListRoute>()
            MaterialListScreen(
                tripId = route.tripId,
                onNavigateBack = { navController.popBackStack() },
            )
        }
        composable<SharedViewRoute> { backStackEntry ->
            val route = backStackEntry.toRoute<SharedViewRoute>()
            TravelogueScreen(
                shareCode = route.shareCode,
                onNavigateBack = { navController.popBackStack() },
            )
        }

        // Profile
        composable<ProfileRoute> {
            ProfileScreen(onNavigateBack = { navController.popBackStack() })
        }
    }
}

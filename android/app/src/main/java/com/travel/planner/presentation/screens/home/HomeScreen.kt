package com.travel.planner.presentation.screens.home

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.compose.viewModel
import com.travel.planner.domain.model.PaginatedData
import com.travel.planner.domain.model.PlanSummary
import com.travel.planner.domain.model.Trip
import com.travel.planner.domain.repository.AuthRepository
import com.travel.planner.domain.repository.PlanRepository
import com.travel.planner.domain.repository.TripRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HomeScreen(
    onNavigateToChat: () -> Unit,
    onNavigateToPlanDetail: (String) -> Unit,
    onNavigateToTrip: (String) -> Unit,
    onNavigateToTravelogue: (String) -> Unit,
    onNavigateToProfile: () -> Unit,
    onLogout: () -> Unit,
    viewModel: HomeViewModel = hiltViewModel(),
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    LaunchedEffect(Unit) {
        viewModel.load()
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("AI旅行规划师") },
                actions = {
                    IconButton(onClick = onNavigateToProfile) {
                        Icon(Icons.Default.Person, contentDescription = "Profile")
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.primaryContainer,
                ),
            )
        },
        floatingActionButton = {
            ExtendedFloatingActionButton(
                onClick = onNavigateToChat,
                icon = { Icon(Icons.Default.Chat, contentDescription = null) },
                text = { Text("开始规划") },
                containerColor = MaterialTheme.colorScheme.primary,
                contentColor = MaterialTheme.colorScheme.onPrimary,
            )
        },
    ) { padding ->
        when (val state = uiState) {
            is HomeUiState.Loading -> {
                Box(Modifier.fillMaxSize().padding(padding), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator()
                }
            }
            is HomeUiState.Success -> {
                LazyColumn(
                    modifier = Modifier.fillMaxSize().padding(padding),
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(16.dp),
                ) {
                    // Quick Actions
                    item {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(12.dp),
                        ) {
                            QuickActionCard(
                                icon = Icons.Default.Chat,
                                label = "AI规划",
                                onClick = onNavigateToChat,
                                modifier = Modifier.weight(1f),
                            )
                            QuickActionCard(
                                icon = Icons.Default.Map,
                                label = "我的方案",
                                onClick = {},
                                modifier = Modifier.weight(1f),
                            )
                            QuickActionCard(
                                icon = Icons.Default.DirectionsWalk,
                                label = "行程中",
                                onClick = {},
                                modifier = Modifier.weight(1f),
                            )
                        }
                    }

                    // Active Trips
                    if (state.activeTrips.isNotEmpty()) {
                        item {
                            Text(
                                text = "进行中的行程",
                                style = MaterialTheme.typography.titleMedium,
                            )
                        }
                        items(state.activeTrips) { trip ->
                            TripCard(
                                trip = trip,
                                onClick = { onNavigateToTrip(trip.id) },
                            )
                        }
                    }

                    // Recent Plans
                    if (state.recentPlans.isNotEmpty()) {
                        item {
                            Text(
                                text = "最近方案",
                                style = MaterialTheme.typography.titleMedium,
                            )
                        }
                        items(state.recentPlans) { plan ->
                            PlanCard(
                                plan = plan,
                                onClick = { onNavigateToPlanDetail(plan.id) },
                            )
                        }
                    }

                    // Logout
                    item {
                        TextButton(onClick = {
                            viewModel.logout()
                            onLogout()
                        }) {
                            Text("退出登录", color = MaterialTheme.colorScheme.error)
                        }
                    }
                }
            }
            is HomeUiState.Error -> {
                Box(Modifier.fillMaxSize().padding(padding), contentAlignment = Alignment.Center) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Text(state.message, color = MaterialTheme.colorScheme.error)
                        Spacer(Modifier.height(8.dp))
                        Button(onClick = { viewModel.load() }) { Text("重试") }
                    }
                }
            }
        }
    }
}

@Composable
private fun QuickActionCard(
    icon: ImageVector,
    label: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Card(
        modifier = modifier.clickable(onClick = onClick),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Icon(icon, contentDescription = label, tint = MaterialTheme.colorScheme.primary)
            Spacer(Modifier.height(8.dp))
            Text(label, style = MaterialTheme.typography.labelLarge)
        }
    }
}

@Composable
private fun TripCard(trip: Trip, onClick: () -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth().clickable(onClick = onClick),
    ) {
        Row(
            modifier = Modifier.padding(16.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(
                Icons.Default.DirectionsWalk,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.primary,
            )
            Spacer(Modifier.width(12.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    "Day ${trip.currentDay}",
                    style = MaterialTheme.typography.titleMedium,
                )
                Text(
                    "已打卡 ${trip.checkedIn}/${trip.totalPois} · 剩余 ¥${trip.budgetRemain.toInt()}",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            Icon(Icons.Default.ChevronRight, contentDescription = null)
        }
    }
}

@Composable
private fun PlanCard(plan: PlanSummary, onClick: () -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth().clickable(onClick = onClick),
    ) {
        Row(
            modifier = Modifier.padding(16.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(
                Icons.Default.Map,
                contentDescription = null,
                tint = if (plan.isFavorite) MaterialTheme.colorScheme.error
                    else MaterialTheme.colorScheme.primary,
            )
            Spacer(Modifier.width(12.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    plan.title.ifEmpty { plan.destination },
                    style = MaterialTheme.typography.titleMedium,
                )
                Text(
                    "${plan.days}天 · 预估 ¥${plan.estimatedCost.toInt()}",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            Icon(Icons.Default.ChevronRight, contentDescription = null)
        }
    }
}

// ---- ViewModel ----

sealed class HomeUiState {
    data object Loading : HomeUiState()
    data class Success(
        val activeTrips: List<Trip> = emptyList(),
        val recentPlans: List<PlanSummary> = emptyList(),
    ) : HomeUiState()
    data class Error(val message: String) : HomeUiState()
}

@HiltViewModel
class HomeViewModel @Inject constructor(
    private val planRepository: PlanRepository,
    private val tripRepository: TripRepository,
    private val authRepository: AuthRepository,
) : ViewModel() {

    private val _uiState = MutableStateFlow<HomeUiState>(HomeUiState.Loading)
    val uiState: StateFlow<HomeUiState> = _uiState.asStateFlow()

    fun load() {
        viewModelScope.launch {
            _uiState.value = HomeUiState.Loading
            try {
                val plans = planRepository.listPlans().getOrDefault(PaginatedData())
                val trips = tripRepository.listTrips(status = "active").getOrDefault(PaginatedData())
                _uiState.value = HomeUiState.Success(
                    activeTrips = trips.list,
                    recentPlans = plans.list,
                )
            } catch (e: Exception) {
                _uiState.value = HomeUiState.Error(e.message ?: "加载失败")
            }
        }
    }

    fun logout() {
        viewModelScope.launch { authRepository.logout() }
    }
}

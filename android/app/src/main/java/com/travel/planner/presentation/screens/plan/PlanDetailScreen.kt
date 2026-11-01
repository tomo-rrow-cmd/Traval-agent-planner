package com.travel.planner.presentation.screens.plan

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.compose.viewModel
import com.travel.planner.domain.model.*
import com.travel.planner.domain.repository.PlanRepository
import com.travel.planner.presentation.components.common.LoadingIndicator
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PlanDetailScreen(
    planId: String,
    onStartTrip: (String) -> Unit,
    onNavigateBack: () -> Unit,
    viewModel: PlanDetailViewModel = hiltViewModel(),
) {
    LaunchedEffect(planId) { viewModel.load(planId) }
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(uiState.plan?.title ?: "方案详情") },
                navigationIcon = {
                    IconButton(onClick = onNavigateBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Back")
                    }
                },
                actions = {
                    IconButton(onClick = { viewModel.export("md") }) {
                        Icon(Icons.Default.Download, contentDescription = "Export")
                    }
                    IconButton(onClick = { viewModel.share() }) {
                        Icon(Icons.Default.Share, contentDescription = "Share")
                    }
                },
            )
        },
    ) { padding ->
        val state = uiState
        when {
            state.isLoading -> LoadingIndicator(Modifier.padding(padding))
            state.error != null -> {
                Box(Modifier.fillMaxSize().padding(padding), contentAlignment = Alignment.Center) {
                    Text(state.error, color = MaterialTheme.colorScheme.error)
                }
            }
            state.plan != null -> {
                val plan = state.plan
                LazyColumn(
                    modifier = Modifier.fillMaxSize().padding(padding),
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    item {
                        Card {
                            Row(Modifier.padding(16.dp)) {
                                InfoChip(Icons.Default.CalendarMonth, "${plan.days}天")
                                Spacer(Modifier.width(8.dp))
                                InfoChip(Icons.Default.Person, "${plan.peopleCount}人")
                                Spacer(Modifier.width(8.dp))
                                InfoChip(Icons.Default.Wallet, "¥${plan.totalBudget.toInt()}")
                            }
                        }
                    }

                    item { Text("每日行程", style = MaterialTheme.typography.titleMedium) }

                    items(plan.dailyItinerary) { day ->
                        DayCard(day)
                    }

                    item {
                        Button(
                            onClick = {
                                viewModel.startTrip { tripId -> onStartTrip(tripId) }
                            },
                            modifier = Modifier.fillMaxWidth().height(50.dp),
                        ) {
                            Text("开始旅行")
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun InfoChip(icon: ImageVector, text: String) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Icon(icon, contentDescription = null, modifier = Modifier.size(16.dp))
        Spacer(Modifier.width(4.dp))
        Text(text, style = MaterialTheme.typography.bodySmall)
    }
}

@Composable
private fun DayCard(day: DayPlan) {
    Card {
        Column(Modifier.padding(12.dp)) {
            Text("Day ${day.day}", style = MaterialTheme.typography.titleMedium)
            day.attractions.forEach { attr ->
                Row(Modifier.padding(vertical = 4.dp)) {
                    Icon(Icons.Default.Place, null, Modifier.size(18.dp))
                    Spacer(Modifier.width(8.dp))
                    Column {
                        Text(attr.name, style = MaterialTheme.typography.bodyMedium)
                        Text(attr.reason, style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
            }
            if (day.meals.isNotEmpty()) {
                HorizontalDivider(Modifier.padding(vertical = 4.dp))
                day.meals.forEach { meal ->
                    Text("${meal.meal}: ${meal.restaurant}",
                        style = MaterialTheme.typography.bodySmall)
                }
            }
        }
    }
}

// ---- ViewModel ----

data class PlanDetailUiState(
    val isLoading: Boolean = true,
    val plan: PlanDetail? = null,
    val error: String? = null,
)

@HiltViewModel
class PlanDetailViewModel @Inject constructor(
    private val planRepository: PlanRepository,
) : ViewModel() {

    private val _uiState = MutableStateFlow(PlanDetailUiState())
    val uiState: StateFlow<PlanDetailUiState> = _uiState.asStateFlow()

    fun load(planId: String) {
        viewModelScope.launch {
            planRepository.getPlan(planId)
                .onSuccess { plan -> _uiState.value = PlanDetailUiState(isLoading = false, plan = plan) }
                .onFailure { e -> _uiState.value = PlanDetailUiState(isLoading = false, error = e.message) }
        }
    }

    fun startTrip(onStarted: (String) -> Unit) {
        val plan = _uiState.value.plan ?: return
        viewModelScope.launch {
            planRepository.startTrip(plan.id)
                .onSuccess { trip -> onStarted(trip.id) }
                .onFailure { e -> _uiState.value = _uiState.value.copy(error = e.message) }
        }
    }

    fun export(format: String) { /* export via Android share sheet */ }
    fun share() { /* generate share link */ }
}

# Android Frontend Development Skill
# For: Claude / AI Assistant
# Version: 2026.07
# Focus: Jetpack Compose + Kotlin + Modern Android Architecture

## 1. 核心原则

- **Compose-first**: 2026年所有新Android项目必须使用Jetpack Compose，XML仅用于维护旧代码。
- **声明式UI**: UI是状态的纯函数。当状态改变，Compose自动重组。禁止手动操作视图（findViewById/setText）。
- **单向数据流**: State → UI → Event → State。使用ViewModel + StateFlow/UiState管理状态。
- **Material Design 3**: 默认使用Material 3组件和动态配色（Dynamic Color）。
- **Kotlin-only**: Compose仅支持Kotlin。使用协程（Coroutines）、Flow、密封类（Sealed Classes）。

## 2. 项目架构标准

### 2.1 模块分层
```
app/
├── presentation/          # UI层 (Compose Screens + ViewModels)
│   ├── screens/
│   ├── components/        # 可复用Composable
│   ├── theme/             # MaterialTheme, ColorScheme, Typography
│   └── viewmodels/
├── domain/                # 业务逻辑层 (UseCases, Models, Repository接口)
├── data/                  # 数据层 (Repository实现, API, Database, DataStore)
└── di/                    # 依赖注入 (Hilt Modules)
```

### 2.2 状态管理规范

**UiState模式（强制）**:
```kotlin
// 使用密封类定义所有UI状态
sealed class HomeUiState {
    data object Loading : HomeUiState()
    data class Success(val items: List<Item>) : HomeUiState()
    data class Error(val message: String) : HomeUiState()
}

// ViewModel
@HiltViewModel
class HomeViewModel @Inject constructor(
    private val getItemsUseCase: GetItemsUseCase
) : ViewModel() {

    private val _uiState = MutableStateFlow<HomeUiState>(HomeUiState.Loading)
    val uiState: StateFlow<HomeUiState> = _uiState.asStateFlow()

    init { loadItems() }

    private fun loadItems() {
        viewModelScope.launch {
            getItemsUseCase()
                .onStart { _uiState.value = HomeUiState.Loading }
                .catch { e -> _uiState.value = HomeUiState.Error(e.message ?: "Unknown") }
                .collect { items -> _uiState.value = HomeUiState.Success(items) }
        }
    }
}

// Screen Composable
@Composable
fun HomeScreen(viewModel: HomeViewModel = hiltViewModel()) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    when (val state = uiState) {
        is HomeUiState.Loading -> CircularProgressIndicator()
        is HomeUiState.Success -> ItemList(items = state.items)
        is HomeUiState.Error -> ErrorMessage(message = state.message)
    }
}
```

**关键规则**:
- 使用 `collectAsStateWithLifecycle()` 而非 `collectAsState()`，确保生命周期安全。
- ViewModel绝不可引用Composable。所有状态通过StateFlow暴露。
- 使用 `rememberSaveable` 保存配置变更（如屏幕旋转）中的UI状态。

## 3. Compose UI 编写规范

### 3.1 Composable函数签名
```kotlin
// ✅ 正确：状态提升（State Hoisting）
@Composable
fun UserCard(
    user: User,
    onClick: () -> Unit,
    modifier: Modifier = Modifier  // 必须提供Modifier参数
) {
    Card(
        modifier = modifier.clickable(onClick = onClick),
        // ...
    ) { /* content */ }
}

// ❌ 错误：内部持有状态，不接收Modifier
@Composable
fun BadUserCard() {  // 没有Modifier参数
    var expanded by remember { mutableStateOf(false) }  // 状态未提升
    // ...
}
```

### 3.2 列表性能（LazyColumn/LazyRow）
```kotlin
// ✅ 正确：使用key和contentType
LazyColumn {
    items(
        items = feedItems,
        key = { it.id },              // 稳定唯一标识，启用高效复用
        contentType = { it.type }      // 不同布局类型区分
    ) { item ->
        when (item.type) {
            FeedType.HEADER -> HeaderItem(item)
            FeedType.POST -> PostItem(item)
            FeedType.AD -> AdItem(item)
        }
    }
}
```
- 始终为`items()`提供`key`参数。
- 使用`contentType`区分不同布局类型。
- 避免在LazyColumn中嵌套Scrollable组件。

### 3.3 图片加载
```kotlin
// 使用Coil（标准库）
implementation("io.coil-kt:coil-compose:2.x.x")

AsyncImage(
    model = ImageRequest.Builder(LocalContext.current)
        .data(imageUrl)
        .crossfade(true)
        .placeholder(R.drawable.placeholder)
        .build(),
    contentDescription = description,  // 必须提供，无障碍要求
    modifier = Modifier.fillMaxWidth(),
    contentScale = ContentScale.Crop
)
```

### 3.4 导航（Type-Safe Navigation）
```kotlin
// 使用Kotlin Serialization定义路由（Navigation 2.8+）
@Serializable
object HomeRoute

@Serializable
data class DetailRoute(val itemId: String)

@Composable
fun AppNavigation() {
    val navController = rememberNavController()

    NavHost(navController = navController, startDestination = HomeRoute) {
        composable<HomeRoute> { HomeScreen() }
        composable<DetailRoute> { backStackEntry ->
            val detail = backStackEntry.toRoute<DetailRoute>()
            DetailScreen(itemId = detail.itemId)
        }
    }
}

// 跳转
navController.navigate(DetailRoute(itemId = "123"))
```

### 3.5 主题与样式
```kotlin
// 使用MaterialTheme，禁止硬编码颜色/字体
@Composable
fun MyAppTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    dynamicColor: Boolean = true,  // 启用动态配色（Android 12+）
    content: @Composable () -> Unit
) {
    val colorScheme = when {
        dynamicColor && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S -> {
            val context = LocalContext.current
            if (darkTheme) dynamicDarkColorScheme(context) else dynamicLightColorScheme(context)
        }
        darkTheme -> DarkColorScheme
        else -> LightColorScheme
    }

    MaterialTheme(
        colorScheme = colorScheme,
        typography = AppTypography,
        shapes = AppShapes,
        content = content
    )
}

// 使用Theme值，禁止硬编码
Text(
    text = "Hello",
    style = MaterialTheme.typography.headlineMedium,  // ✅
    color = MaterialTheme.colorScheme.primary         // ✅
)
```

## 4. 依赖注入（Hilt）

```kotlin
// ViewModel注入
@HiltViewModel
class MyViewModel @Inject constructor(
    private val repository: MyRepository
) : ViewModel() { /* ... */ }

// Screen中使用
@Composable
fun MyScreen(viewModel: MyViewModel = hiltViewModel()) { /* ... */ }

// Repository注入
@Singleton
class MyRepository @Inject constructor(
    private val apiService: ApiService,
    private val dao: MyDao
) { /* ... */ }
```

## 5. 数据层规范

### 5.1 Room数据库
```kotlin
@Entity(tableName = "items")
data class ItemEntity(
    @PrimaryKey val id: String,
    val name: String,
    val createdAt: Long
)

@Dao
interface ItemDao {
    @Query("SELECT * FROM items ORDER BY createdAt DESC")
    fun getAllItems(): Flow<List<ItemEntity>>  // 返回Flow实现自动更新

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAll(items: List<ItemEntity>)
}
```

### 5.2 DataStore（替代SharedPreferences）
```kotlin
val Context.dataStore: DataStore<Preferences> by preferencesDataStore(name = "settings")

// 读写
val THEME_KEY = stringPreferencesKey("theme")
context.dataStore.edit { it[THEME_KEY] = "dark" }
```

### 5.3 Retrofit + OkHttp
```kotlin
@Singleton
class NetworkModule {
    @Provides
    @Singleton
    fun provideOkHttpClient(): OkHttpClient = OkHttpClient.Builder()
        .addInterceptor(HttpLoggingInterceptor().setLevel(HttpLoggingInterceptor.Level.BODY))
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .build()

    @Provides
    @Singleton
    fun provideRetrofit(okHttpClient: OkHttpClient): Retrofit = Retrofit.Builder()
        .baseUrl("https://api.example.com/")
        .client(okHttpClient)
        .addConverterFactory(Json.asConverterFactory("application/json".toMediaType()))
        .build()
}
```

## 6. 动画与交互

```kotlin
// 状态驱动动画
var visible by remember { mutableStateOf(true) }

AnimatedVisibility(
    visible = visible,
    enter = fadeIn() + expandVertically(),
    exit = fadeOut() + shrinkVertically()
) {
    Text("Content")
}

// 手势与滑动
val dismissState = rememberSwipeToDismissBoxState(
    confirmValueChange = { 
        if (it == SwipeToDismissBoxValue.EndToStart) {
            onDelete()
            true
        } else false
    }
)
```

## 7. 测试规范

```kotlin
// Compose UI测试
@HiltAndroidTest
class HomeScreenTest {
    @get:Rule
    val composeTestRule = createAndroidComposeRule<MainActivity>()

    @Test
    fun displayLoadingState() {
        composeTestRule.setContent {
            MyAppTheme { HomeScreen(uiState = HomeUiState.Loading) }
        }
        composeTestRule.onNodeWithTag("loading_indicator").assertExists()
    }

    @Test
    fun displaySuccessState() {
        val items = listOf(Item("1", "Test"))
        composeTestRule.setContent {
            MyAppTheme { HomeScreen(uiState = HomeUiState.Success(items)) }
        }
        composeTestRule.onNodeWithText("Test").assertExists()
    }
}
```
- 使用`testTag`标记需要测试的节点。
- 使用语义树查询：`onNodeWithText`、`onNodeWithContentDescription`。

## 8. 性能优化

- **重组优化**: 使用`@Stable`和`@Immutable`注解标记数据类。函数参数保持稳定引用。
- **Baseline Profiles**: 使用`./gradlew generateBaselineProfile`生成基线配置文件，减少冷启动时间20-30%。
- **避免副作用**: 在Composable中使用`LaunchedEffect`、`SideEffect`、`DisposableEffect`处理副作用，绝不可在Composable中直接调用挂起函数或进行IO操作。
- **强跳过模式**: Compose 1.7+默认启用强跳过模式，接收稳定参数的函数在输入未变时自动跳过重组。

## 9. 常用库清单（2026标准栈）

| 用途 | 库 | 版本策略 |
|------|-----|----------|
| UI框架 | Jetpack Compose (BOM) | 使用BOM统一管理版本 |
| 依赖注入 | Hilt | 配合KSP使用 |
| 网络请求 | Retrofit + Kotlinx Serialization | 替代Gson |
| 图片加载 | Coil | Compose专用 |
| 本地数据库 | Room | 配合KSP |
| 数据存储 | DataStore | 替代SharedPreferences |
| 异步流 | Kotlin Coroutines + Flow | 标准库 |
| 导航 | Navigation Compose | 类型安全路由 |
| 分页 | Paging 3 | Compose集成 |
| 权限处理 | Accompanist Permissions | 或官方API |
| 图表 | MPAndroidChart (via AndroidView) | 或Compose专用图表库 |
| 动画 | Lottie Compose | After Effects动画 |

## 10. 代码生成提示词模板

当用户要求生成Android代码时，按以下顺序确认：
1. 使用Jetpack Compose还是XML？（默认Compose）
2. 使用Hilt进行依赖注入？
3. 需要哪些功能模块？（网络、数据库、图片等）
4. 目标Android最低版本？（默认API 24+）
5. 是否需要Material 3动态配色？

生成代码时遵循：
- 所有Composable必须接收Modifier参数
- 状态必须提升到ViewModel
- 使用collectAsStateWithLifecycle()收集状态
- 使用密封类定义UiState
- 提供Preview注解

## 11. 构建与密钥配置

- 高德地图 Key 不写入仓库，由 Gradle 构建时注入：优先环境变量 `AMAP_KEY`，其次 `android/local.properties`，最后 `-PAMAP_KEY`。
- `android/local.properties` 已被 `.gitignore` 忽略，本地可写入：

```properties
AMAP_KEY=<你的高德Key>
sdk.dir=<Android SDK 路径>
```

- 未配置 Key 时构建仍可完成，但会输出 Gradle 警告，地图相关页面不可用。
- 后端地址通过 `BuildConfig.BASE_URL` 提供，默认 `http://10.0.2.2:8000/api/v1/`（模拟器指向宿主机）；真机调试需改为局域网地址。

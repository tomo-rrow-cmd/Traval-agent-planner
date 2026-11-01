package com.travel.planner.presentation.theme

import android.os.Build
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.platform.LocalContext

private val LightColorScheme = lightColorScheme(
    primary = ColorPrimary,
    onPrimary = ColorOnPrimary,
    primaryContainer = ColorPrimaryContainer,
    secondary = ColorSecondary,
    background = ColorBackground,
    surface = ColorSurface,
    error = ColorError,
)

private val DarkColorScheme = darkColorScheme(
    primary = ColorPrimaryLight,
    onPrimary = ColorOnPrimaryDark,
    primaryContainer = ColorPrimaryContainerDark,
    secondary = ColorSecondaryLight,
    background = ColorBackgroundDark,
    surface = ColorSurfaceDark,
    error = ColorErrorLight,
)

@Composable
fun TravelPlannerTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    dynamicColor: Boolean = true,
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
        content = content,
    )
}

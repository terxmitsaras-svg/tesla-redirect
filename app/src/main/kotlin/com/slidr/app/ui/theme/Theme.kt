package com.slidr.app.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable

private val SlidrColorScheme = darkColorScheme(
    primary = Fuchsia,
    onPrimary = TextPrimary,
    primaryContainer = FuchsiaDim,
    onPrimaryContainer = FuchsiaLight,
    secondary = FuchsiaLight,
    onSecondary = TextPrimary,
    background = Background,
    onBackground = TextPrimary,
    surface = Surface,
    onSurface = TextPrimary,
    surfaceVariant = SurfaceVariant,
    onSurfaceVariant = TextSecondary,
    error = ErrorRed,
    outline = Divider
)

@Composable
fun SlidrTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = SlidrColorScheme,
        typography = SlidrTypography,
        content = content
    )
}

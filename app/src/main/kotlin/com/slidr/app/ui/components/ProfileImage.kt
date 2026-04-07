package com.slidr.app.ui.components

import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import com.slidr.app.ui.theme.Fuchsia

@Composable
fun ProfileImage(
    url: String,
    size: Dp = 48.dp,
    isOnline: Boolean = false,
    showBorder: Boolean = false,
    modifier: Modifier = Modifier
) {
    Box(modifier = modifier) {
        val imageModifier = Modifier
            .size(size)
            .clip(CircleShape)
            .then(
                if (showBorder) Modifier.border(2.dp, Fuchsia, CircleShape) else Modifier
            )

        AsyncImage(
            model = url,
            contentDescription = null,
            contentScale = ContentScale.Crop,
            modifier = imageModifier
        )

        if (isOnline) {
            OnlineIndicator(
                modifier = Modifier.align(Alignment.BottomEnd)
            )
        }
    }
}

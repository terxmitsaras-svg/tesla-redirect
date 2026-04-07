package com.slidr.app.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.slidr.app.ui.theme.Fuchsia
import com.slidr.app.ui.theme.FuchsiaDim
import com.slidr.app.ui.theme.TextSecondary

@Composable
fun TagChip(
    text: String,
    selected: Boolean = false,
    onClick: (() -> Unit)? = null
) {
    val borderColor = if (selected) Fuchsia else TextSecondary.copy(alpha = 0.4f)
    val bgColor = if (selected) FuchsiaDim else Color.Transparent
    val textColor = if (selected) Fuchsia else TextSecondary

    Surface(
        shape = RoundedCornerShape(50),
        border = BorderStroke(1.dp, borderColor),
        color = bgColor,
        modifier = if (onClick != null) Modifier.clickable { onClick() } else Modifier
    ) {
        Text(
            text = text,
            color = textColor,
            fontSize = 12.sp,
            fontWeight = if (selected) FontWeight.Medium else FontWeight.Normal,
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 5.dp)
        )
    }
}

package com.slidr.app.ui.components

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.GridView
import androidx.compose.material.icons.filled.Message
import androidx.compose.material.icons.filled.Person
import androidx.compose.material3.Badge
import androidx.compose.material3.BadgedBox
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.graphics.Color
import androidx.navigation.NavController
import androidx.navigation.compose.currentBackStackEntryAsState
import com.slidr.app.ui.navigation.Screen
import com.slidr.app.ui.theme.Fuchsia
import com.slidr.app.ui.theme.Surface
import com.slidr.app.ui.theme.TextSecondary

@Composable
fun BottomNavBar(navController: NavController, unreadCount: Int = 0) {
    val navBackStack by navController.currentBackStackEntryAsState()
    val currentRoute = navBackStack?.destination?.route

    NavigationBar(containerColor = Surface) {
        NavigationBarItem(
            icon = { Icon(Icons.Filled.GridView, contentDescription = "Discover") },
            label = { Text("Discover") },
            selected = currentRoute == Screen.Home.route,
            onClick = {
                if (currentRoute != Screen.Home.route) {
                    navController.navigate(Screen.Home.route) {
                        popUpTo(Screen.Home.route) { inclusive = true }
                    }
                }
            },
            colors = navBarItemColors()
        )

        NavigationBarItem(
            icon = {
                BadgedBox(
                    badge = {
                        if (unreadCount > 0) {
                            Badge(containerColor = Fuchsia) {
                                Text(unreadCount.toString(), color = Color.White)
                            }
                        }
                    }
                ) {
                    Icon(Icons.Filled.Message, contentDescription = "Messages")
                }
            },
            label = { Text("Messages") },
            selected = currentRoute == Screen.Inbox.route,
            onClick = {
                if (currentRoute != Screen.Inbox.route) {
                    navController.navigate(Screen.Inbox.route)
                }
            },
            colors = navBarItemColors()
        )

        NavigationBarItem(
            icon = { Icon(Icons.Filled.Person, contentDescription = "Profile") },
            label = { Text("Profile") },
            selected = currentRoute == Screen.MyProfile.route,
            onClick = {
                if (currentRoute != Screen.MyProfile.route) {
                    navController.navigate(Screen.MyProfile.route)
                }
            },
            colors = navBarItemColors()
        )
    }
}

@Composable
private fun navBarItemColors() = NavigationBarItemDefaults.colors(
    selectedIconColor = Fuchsia,
    selectedTextColor = Fuchsia,
    unselectedIconColor = TextSecondary,
    unselectedTextColor = TextSecondary,
    indicatorColor = Fuchsia.copy(alpha = 0.15f)
)

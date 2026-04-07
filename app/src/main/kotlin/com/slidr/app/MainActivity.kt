package com.slidr.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.navigation.compose.rememberNavController
import com.slidr.app.ui.navigation.AppNavGraph
import com.slidr.app.ui.navigation.Screen
import com.slidr.app.ui.theme.SlidrTheme

class MainActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            SlidrTheme {
                val app = application as SlidrApplication
                val isLoggedIn by app.container.authRepository.isLoggedIn
                    .collectAsState(initial = false)
                val isProfileSetUp by app.container.authRepository.isProfileSetUp
                    .collectAsState(initial = false)

                val startDestination = when {
                    !isLoggedIn -> Screen.Login.route
                    !isProfileSetUp -> Screen.ProfileSetup.route
                    else -> Screen.Home.route
                }

                val navController = rememberNavController()
                AppNavGraph(
                    navController = navController,
                    startDestination = startDestination,
                    container = app.container
                )
            }
        }
    }
}

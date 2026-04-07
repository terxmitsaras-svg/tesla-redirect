import SwiftUI

@main
struct SlidrApp: App {
    @StateObject private var authRepo = AuthRepository()
    @StateObject private var userRepo = UserRepository()
    @StateObject private var messageRepo = MessageRepository()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(authRepo)
                .environmentObject(userRepo)
                .environmentObject(messageRepo)
                .preferredColorScheme(.dark)
        }
    }
}

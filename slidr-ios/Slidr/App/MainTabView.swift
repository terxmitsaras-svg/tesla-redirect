import SwiftUI

struct MainTabView: View {
    @EnvironmentObject var messageRepo: MessageRepository

    var body: some View {
        TabView {
            HomeView()
                .tabItem {
                    Label("Discover", systemImage: "square.grid.2x2")
                }

            InboxView()
                .tabItem {
                    Label("Messages", systemImage: "message")
                }
                .badge(messageRepo.totalUnread > 0 ? messageRepo.totalUnread : 0)

            MyProfileView()
                .tabItem {
                    Label("Profile", systemImage: "person")
                }
        }
        .tint(.slidrFuchsia)
        .background(Color.slidrBackground)
        .toolbarBackground(Color.slidrSurface, for: .tabBar)
        .toolbarBackground(.visible, for: .tabBar)
    }
}

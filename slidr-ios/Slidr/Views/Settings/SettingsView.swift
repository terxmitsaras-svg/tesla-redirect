import SwiftUI

struct SettingsView: View {
    @EnvironmentObject var authRepo: AuthRepository
    @Environment(\.dismiss) var dismiss

    @State private var showOnlineStatus = true
    @State private var notificationsEnabled = true
    @State private var showLogoutAlert = false

    var body: some View {
        ZStack {
            Color.slidrBackground.ignoresSafeArea()

            List {
                Section {
                    ToggleRow(title: "Show online status",
                              subtitle: "Let others see when you're active",
                              isOn: $showOnlineStatus)
                } header: {
                    Text("Account").sectionHeaderStyle()
                }
                .listRowBackground(Color.slidrSurface)

                Section {
                    ToggleRow(title: "Push notifications",
                              subtitle: "Get notified about new messages",
                              isOn: $notificationsEnabled)
                } header: {
                    Text("Notifications").sectionHeaderStyle()
                }
                .listRowBackground(Color.slidrSurface)

                Section {
                    SimpleRow(title: "Privacy Policy")
                    SimpleRow(title: "Terms of Service")
                    HStack {
                        Text("App version").foregroundColor(.white)
                        Spacer()
                        Text("1.0.0").foregroundColor(.slidrTextSecond)
                    }
                } header: {
                    Text("About").sectionHeaderStyle()
                }
                .listRowBackground(Color.slidrSurface)

                Section {
                    Button {
                        showLogoutAlert = true
                    } label: {
                        Text("Log Out")
                            .foregroundColor(.slidrError)
                            .font(.system(size: 16, weight: .bold))
                            .frame(maxWidth: .infinity)
                    }
                }
                .listRowBackground(Color.slidrSurface)
            }
            .listStyle(.insetGrouped)
            .scrollContentBackground(.hidden)
        }
        .navigationTitle("Settings")
        .navigationBarTitleDisplayMode(.inline)
        .toolbarBackground(Color.slidrBackground, for: .navigationBar)
        .toolbarBackground(.visible, for: .navigationBar)
        .toolbarColorScheme(.dark, for: .navigationBar)
        .alert("Log Out?", isPresented: $showLogoutAlert) {
            Button("Log Out", role: .destructive) {
                authRepo.logout()
            }
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("You'll need to log in again to use Slidr.")
        }
    }
}

struct ToggleRow: View {
    let title: String
    let subtitle: String
    @Binding var isOn: Bool

    var body: some View {
        Toggle(isOn: $isOn) {
            VStack(alignment: .leading, spacing: 2) {
                Text(title).foregroundColor(.white)
                Text(subtitle).font(.system(size: 12)).foregroundColor(.slidrTextSecond)
            }
        }
        .tint(.slidrFuchsia)
    }
}

struct SimpleRow: View {
    let title: String

    var body: some View {
        HStack {
            Text(title).foregroundColor(.white)
            Spacer()
            Image(systemName: "chevron.right").font(.system(size: 12)).foregroundColor(.slidrTextSecond)
        }
    }
}

extension Text {
    func sectionHeaderStyle() -> some View {
        self
            .font(.system(size: 11, weight: .medium))
            .foregroundColor(Color.slidrTextSecond)
            .textCase(.uppercase)
            .tracking(1.5)
    }
}

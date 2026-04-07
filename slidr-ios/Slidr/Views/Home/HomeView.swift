import SwiftUI

struct HomeView: View {
    @EnvironmentObject var userRepo: UserRepository

    @State private var showFilters = false
    @State private var onlineOnly = false
    @State private var minAge: Double = 18
    @State private var maxAge: Double = 65
    @State private var maxDistance: Double = 10

    let columns = Array(repeating: GridItem(.flexible(), spacing: 2), count: 3)

    var filteredUsers: [User] {
        userRepo.nearbyUsers.filter { user in
            (!onlineOnly || user.isOnline) &&
            user.age >= Int(minAge) && user.age <= Int(maxAge) &&
            user.distanceKm <= maxDistance
        }
    }

    var body: some View {
        NavigationStack {
            ZStack {
                Color.slidrBackground.ignoresSafeArea()

                ScrollView {
                    LazyVGrid(columns: columns, spacing: 2) {
                        ForEach(filteredUsers) { user in
                            NavigationLink(destination: UserProfileView(user: user)) {
                                UserGridCard(user: user) {}
                            }
                            .buttonStyle(.plain)
                        }
                    }
                }
            }
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Text("slidr")
                        .font(.system(size: 26, weight: .black))
                        .foregroundColor(.slidrFuchsia)
                        .tracking(-1)
                }
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button { showFilters = true } label: {
                        Image(systemName: "slider.horizontal.3")
                            .foregroundColor(.white)
                    }
                }
            }
            .toolbarBackground(Color.slidrBackground, for: .navigationBar)
            .toolbarBackground(.visible, for: .navigationBar)
            .sheet(isPresented: $showFilters) {
                FilterSheet(
                    onlineOnly: $onlineOnly,
                    minAge: $minAge,
                    maxAge: $maxAge,
                    maxDistance: $maxDistance,
                    onApply: { showFilters = false },
                    onReset: {
                        onlineOnly = false; minAge = 18; maxAge = 65; maxDistance = 10
                    }
                )
                .presentationDetents([.medium, .large])
                .presentationBackground(Color.slidrSurface)
            }
        }
    }
}

struct FilterSheet: View {
    @Binding var onlineOnly: Bool
    @Binding var minAge: Double
    @Binding var maxAge: Double
    @Binding var maxDistance: Double
    let onApply: () -> Void
    let onReset: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 20) {
            Text("Filters")
                .font(.system(size: 20, weight: .bold))
                .foregroundColor(.white)
                .padding(.top, 24)

            VStack(alignment: .leading, spacing: 6) {
                Text("Age: \(Int(minAge)) – \(Int(maxAge))")
                    .font(.system(size: 14))
                    .foregroundColor(.slidrTextSecond)
                HStack {
                    Slider(value: $minAge, in: 18...65, step: 1)
                        .tint(.slidrFuchsia)
                    Slider(value: $maxAge, in: 18...65, step: 1)
                        .tint(.slidrFuchsia)
                }
            }

            VStack(alignment: .leading, spacing: 6) {
                Text("Max distance: \(Int(maxDistance)) km")
                    .font(.system(size: 14))
                    .foregroundColor(.slidrTextSecond)
                Slider(value: $maxDistance, in: 1...50, step: 1)
                    .tint(.slidrFuchsia)
            }

            Toggle(isOn: $onlineOnly) {
                Text("Online only")
                    .foregroundColor(.white)
                    .font(.system(size: 15))
            }
            .tint(.slidrFuchsia)

            Spacer()

            HStack(spacing: 12) {
                Button(action: onReset) {
                    Text("Reset")
                        .foregroundColor(.slidrTextSecond)
                        .frame(maxWidth: .infinity)
                        .frame(height: 48)
                        .background(Color.slidrSurfaceVar)
                        .cornerRadius(12)
                }
                Button(action: onApply) {
                    Text("Apply")
                        .font(.system(size: 16, weight: .bold))
                        .foregroundColor(.white)
                        .frame(maxWidth: .infinity)
                        .frame(height: 48)
                        .background(Color.slidrFuchsia)
                        .cornerRadius(12)
                }
            }
            .padding(.bottom, 24)
        }
        .padding(.horizontal, 24)
    }
}

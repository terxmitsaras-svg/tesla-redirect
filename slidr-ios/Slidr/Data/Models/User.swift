import Foundation

struct User: Identifiable, Equatable {
    let id: String
    var displayName: String
    var age: Int
    var bio: String
    var avatarURL: String
    var distanceKm: Double
    var isOnline: Bool
    var height: String
    var bodyType: String
    var pronouns: String
    var lookingFor: [String]
    var tags: [String]
    var isFavorite: Bool = false

    var distanceLabel: String {
        if distanceKm < 1 {
            return "\(Int(distanceKm * 1000))m"
        } else {
            return String(format: "%.1fkm", distanceKm)
        }
    }
}

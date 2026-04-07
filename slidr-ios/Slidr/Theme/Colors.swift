import SwiftUI

extension Color {
    static let slidrBackground   = Color(hex: "0D0D0D")
    static let slidrSurface      = Color(hex: "1A1A1A")
    static let slidrSurfaceVar   = Color(hex: "242424")
    static let slidrFuchsia      = Color(hex: "E91E8C")
    static let slidrFuchsiaLight = Color(hex: "FF4DB2")
    static let slidrFuchsiaDim   = Color(hex: "E91E8C").opacity(0.2)
    static let slidrOnline       = Color(hex: "2ECC71")
    static let slidrTextPrimary  = Color.white
    static let slidrTextSecond   = Color(hex: "AAAAAA")
    static let slidrDivider      = Color(hex: "2A2A2A")
    static let slidrError        = Color(hex: "FF4444")

    init(hex: String) {
        let hex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var int: UInt64 = 0
        Scanner(string: hex).scanHexInt64(&int)
        let a, r, g, b: UInt64
        switch hex.count {
        case 3:
            (a, r, g, b) = (255, (int >> 8) * 17, (int >> 4 & 0xF) * 17, (int & 0xF) * 17)
        case 6:
            (a, r, g, b) = (255, int >> 16, int >> 8 & 0xFF, int & 0xFF)
        case 8:
            (a, r, g, b) = (int >> 24, int >> 16 & 0xFF, int >> 8 & 0xFF, int & 0xFF)
        default:
            (a, r, g, b) = (1, 1, 1, 0)
        }
        self.init(
            .sRGB,
            red: Double(r) / 255,
            green: Double(g) / 255,
            blue: Double(b) / 255,
            opacity: Double(a) / 255
        )
    }
}

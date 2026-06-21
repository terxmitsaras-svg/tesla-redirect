#include "string_utils.h"

#include <cctype>
#include <cstdint>
#include <unordered_map>

namespace posokanei {

// Map: Unicode code point → UTF-8 replacement string (lowercase, no diacritics)
// Covers the Greek and Coptic block (U+0386–U+03CE) that appears in modern
// monotonic Greek text.  Polytonic (U+1F00–U+1FFF) is left unchanged; it
// rarely appears in supermarket product names.
static const std::unordered_map<uint16_t, const char*>& normMap() {
    static const std::unordered_map<uint16_t, const char*> kMap = {
        // ── Accented uppercase → lowercase base ─────────────────────────
        {0x0386, "\xCE\xB1"}, // Ά → α
        {0x0388, "\xCE\xB5"}, // Έ → ε
        {0x0389, "\xCE\xB7"}, // Ή → η
        {0x038A, "\xCE\xB9"}, // Ί → ι
        {0x038C, "\xCE\xBF"}, // Ό → ο
        {0x038E, "\xCF\x85"}, // Ύ → υ
        {0x038F, "\xCF\x89"}, // Ώ → ω
        // ── Uppercase with dialytika → lowercase base ────────────────────
        {0x03AA, "\xCE\xB9"}, // Ϊ → ι
        {0x03AB, "\xCF\x85"}, // Ϋ → υ
        // ── Plain uppercase → lowercase ──────────────────────────────────
        {0x0391, "\xCE\xB1"}, // Α
        {0x0392, "\xCE\xB2"}, // Β
        {0x0393, "\xCE\xB3"}, // Γ
        {0x0394, "\xCE\xB4"}, // Δ
        {0x0395, "\xCE\xB5"}, // Ε
        {0x0396, "\xCE\xB6"}, // Ζ
        {0x0397, "\xCE\xB7"}, // Η
        {0x0398, "\xCE\xB8"}, // Θ
        {0x0399, "\xCE\xB9"}, // Ι
        {0x039A, "\xCE\xBA"}, // Κ
        {0x039B, "\xCE\xBB"}, // Λ
        {0x039C, "\xCE\xBC"}, // Μ
        {0x039D, "\xCE\xBD"}, // Ν
        {0x039E, "\xCE\xBE"}, // Ξ
        {0x039F, "\xCE\xBF"}, // Ο
        {0x03A0, "\xCF\x80"}, // Π
        {0x03A1, "\xCF\x81"}, // Ρ
        {0x03A3, "\xCF\x83"}, // Σ
        {0x03A4, "\xCF\x84"}, // Τ
        {0x03A5, "\xCF\x85"}, // Υ
        {0x03A6, "\xCF\x86"}, // Φ
        {0x03A7, "\xCF\x87"}, // Χ
        {0x03A8, "\xCF\x88"}, // Ψ
        {0x03A9, "\xCF\x89"}, // Ω
        // ── Lowercase accented → lowercase base ──────────────────────────
        {0x0390, "\xCE\xB9"}, // ΐ (dialytika + tonos)
        {0x03AC, "\xCE\xB1"}, // ά
        {0x03AD, "\xCE\xB5"}, // έ
        {0x03AE, "\xCE\xB7"}, // ή
        {0x03AF, "\xCE\xB9"}, // ί
        {0x03B0, "\xCF\x85"}, // ΰ (dialytika + tonos)
        {0x03CA, "\xCE\xB9"}, // ϊ (dialytika)
        {0x03CB, "\xCF\x85"}, // ϋ (dialytika)
        {0x03CC, "\xCE\xBF"}, // ό
        {0x03CD, "\xCF\x85"}, // ύ
        {0x03CE, "\xCF\x89"}, // ώ
    };
    return kMap;
}

std::string normalizeGreek(const std::string& text) {
    std::string result;
    result.reserve(text.size());

    const auto& kMap = normMap();

    for (std::size_t i = 0; i < text.size(); ) {
        auto byte = static_cast<unsigned char>(text[i]);

        if (byte < 0x80) {
            // ASCII: just lowercase
            result += static_cast<char>(
                std::tolower(static_cast<unsigned char>(byte)));
            ++i;
        } else if ((byte & 0xE0u) == 0xC0u && i + 1 < text.size()) {
            // 2-byte UTF-8 sequence
            auto b2 = static_cast<unsigned char>(text[i + 1]);
            uint16_t cp = static_cast<uint16_t>(((byte & 0x1Fu) << 6u) | (b2 & 0x3Fu));

            auto it = kMap.find(cp);
            if (it != kMap.end()) {
                result += it->second; // normalized replacement
            } else {
                result += static_cast<char>(byte);
                result += static_cast<char>(b2);
            }
            i += 2;
        } else if ((byte & 0xF0u) == 0xE0u && i + 2 < text.size()) {
            // 3-byte (e.g. polytonic Greek, CJK): pass through unchanged
            result += static_cast<char>(byte);
            result += text[i + 1];
            result += text[i + 2];
            i += 3;
        } else if ((byte & 0xF8u) == 0xF0u && i + 3 < text.size()) {
            // 4-byte (emoji, etc.): pass through unchanged
            result += static_cast<char>(byte);
            result += text[i + 1];
            result += text[i + 2];
            result += text[i + 3];
            i += 4;
        } else {
            // Invalid or lone continuation byte: skip
            ++i;
        }
    }

    return result;
}

bool containsNormalized(const std::string& haystack, const std::string& needle) {
    if (needle.empty()) return true;
    const auto nh = normalizeGreek(haystack);
    const auto nn = normalizeGreek(needle);
    return nh.find(nn) != std::string::npos;
}

} // namespace posokanei

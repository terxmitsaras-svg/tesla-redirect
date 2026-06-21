#include "price_utils.h"

#include <algorithm>
#include <cassert>
#include <cctype>
#include <cstdio>
#include <limits>
#include <stdexcept>

namespace posokanei {

double parsePrice(const std::string& text) {
    // Pass 1: extract the first contiguous run of digits and separators (,.)
    std::string numeric;
    bool in_number = false;

    for (std::size_t i = 0; i < text.size(); ) {
        auto byte = static_cast<unsigned char>(text[i]);

        if (byte < 0x80) {
            // ASCII
            char c = static_cast<char>(byte);
            if (std::isdigit(static_cast<unsigned char>(c))) {
                numeric += c;
                in_number = true;
                ++i;
            } else if (in_number && (c == ',' || c == '.')) {
                numeric += c;
                ++i;
            } else if (in_number) {
                break; // stop at first non-numeric character after the number
            } else {
                ++i; // skip leading non-numeric characters
            }
        } else {
            // UTF-8 multibyte (€, α, etc.): advance without recording
            if      ((byte & 0xE0u) == 0xC0u) i += 2;
            else if ((byte & 0xF0u) == 0xE0u) i += 3;
            else if ((byte & 0xF8u) == 0xF0u) i += 4;
            else                               ++i;
            if (in_number) break;
        }
    }

    // Trim trailing separators left by "3,00 €/kg" → extracted "3,00,"
    while (!numeric.empty() && (numeric.back() == ',' || numeric.back() == '.')) {
        numeric.pop_back();
    }

    if (numeric.empty()) return -1.0;

    auto last_comma = numeric.rfind(',');
    auto last_dot   = numeric.rfind('.');
    const auto npos = std::string::npos;

    try {
        if (last_comma == npos && last_dot == npos) {
            return std::stod(numeric);
        }

        if (last_comma != npos && last_dot != npos) {
            // Both present: the later one is the decimal separator
            if (last_comma > last_dot) {
                // European "1.234,56"
                auto s = numeric;
                s.erase(std::remove(s.begin(), s.end(), '.'), s.end());
                s[s.rfind(',')] = '.';
                return std::stod(s);
            } else {
                // Anglo "1,234.56"
                auto s = numeric;
                s.erase(std::remove(s.begin(), s.end(), ','), s.end());
                return std::stod(s);
            }
        }

        if (last_comma != npos) {
            std::size_t decimals = numeric.size() - last_comma - 1;
            if (decimals <= 2) {
                // "2,49" or "3,0" → comma is decimal separator
                auto s = numeric;
                s[last_comma] = '.';
                return std::stod(s);
            }
            // "1,000" → comma is thousands separator
            auto s = numeric;
            s.erase(std::remove(s.begin(), s.end(), ','), s.end());
            return std::stod(s);
        }

        // Only a dot
        std::size_t decimals = numeric.size() - last_dot - 1;
        bool multiple_dots   = (numeric.find('.') != last_dot);
        if (decimals == 3 && !multiple_dots) {
            // "1.000" → thousands dot
            auto s = numeric;
            s.erase(std::remove(s.begin(), s.end(), '.'), s.end());
            return std::stod(s);
        }
        return std::stod(numeric);

    } catch (...) {
        return -1.0;
    }
}

std::string formatPrice(double price) {
    // Greek convention: decimal comma, two decimal places, euro sign
    char buf[32];
    // Format with a regular period first, then swap it to a comma
    std::snprintf(buf, sizeof(buf), "%.2f €", price);
    for (char* p = buf; *p; ++p) {
        if (*p == '.') { *p = ','; break; }
    }
    return buf;
}

int findCheapestIndex(const std::vector<double>& prices) {
    if (prices.empty()) return -1;
    auto it = std::min_element(prices.begin(), prices.end());
    return static_cast<int>(it - prices.begin());
}

} // namespace posokanei

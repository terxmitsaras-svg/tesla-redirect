package gr.posokanei4real.app.utils

object NativeUtils {

    init {
        System.loadLibrary("posokanei")
    }

    /** Parse a price string (e.g. "2,49 €") → Double, or -1.0 on failure. */
    external fun parsePrice(text: String): Double

    /** Format a Double as a Greek price string (e.g. "2,49 €"). */
    external fun formatPrice(price: Double): String

    /** Index of the cheapest price in the array; -1 if empty. */
    external fun findCheapestIndex(prices: DoubleArray): Int

    /** Lowercase + strip diacritics from Greek UTF-8 text. */
    external fun normalizeGreek(text: String): String

    /** True if [haystack] contains [needle] after both are normalized. */
    external fun containsNormalized(haystack: String, needle: String): Boolean
}

package io.stormi.support.platform.collection.hash

import kotlinx.cinterop.COpaquePointer
import kotlinx.cinterop.ExperimentalForeignApi
import kotlinx.cinterop.UIntVar
import kotlinx.cinterop.get
import kotlinx.cinterop.reinterpret
import kotlin.experimental.ExperimentalNativeApi
import kotlin.math.abs

// --- 프로빙 타입 상수 ---
const val PROBING_TYPE_QUADRATIC = 0
const val PROBING_TYPE_DOUBLE_HASHING = 1

// --- 기존 상수 ---
const val BYTE_MASK = 0xFF
const val P_MODULUS: Long = 4294967311L

/**
 * Tabulation Hashing 네이티브 구현. (변경 없음)
 */
@OptIn(ExperimentalNativeApi::class, ExperimentalForeignApi::class)
@CName("elastic_tabulation_hash")
fun elasticTabulationHashNative(
    keyHashCode: Long,
    tableDataPtr: COpaquePointer?,
    tableCount: Int,
    tableBucketSize: Int,
    byteShift: Int,
): Long {
    if (tableDataPtr == null) {
        return keyHashCode
    }
    val tableData = tableDataPtr.reinterpret<UIntVar>()
    var result = 0L
    for (i in 0 until tableCount) {
        val byteVal = (keyHashCode shr (i * byteShift)).toInt() and BYTE_MASK
        val tableIndex = i * tableBucketSize + byteVal
        val currentTotalTableSize = tableCount * tableBucketSize
        if (tableIndex < 0 || tableIndex >= currentTotalTableSize) {
            throw IndexOutOfBoundsException(
                "Table index out of bounds: $tableIndex (total size: $currentTotalTableSize). " +
                        "Key byte value was $byteVal for byte index $i. " +
                        "Params: tableCount=$tableCount, tableBucketSize=$tableBucketSize, byteShift=$byteShift"
            )
        }
        result = result xor tableData[tableIndex].toLong()
    }
    return result
}

/**
 * Universal Hashing 네이티브 구현. (변경 없음)
 */
@OptIn(ExperimentalNativeApi::class)
@CName("funnel_universal_hash")
fun funnelUniversalHashNative(keyHashCode: Long, a: Long, b: Long): Long {
    val axModPLong = multiplyMod64(a, keyHashCode, P_MODULUS)
    var hashValLong = axModPLong + b
    hashValLong = (hashValLong % P_MODULUS + P_MODULUS) % P_MODULUS
    return hashValLong
}

/**
 * 다음 탐사 위치(인덱스)를 계산하는 네이티브 함수.
 *
 * @param probingType 탐사 방식 (0: Quadratic, 1: Double Hashing).
 * @param keyHash1 키의 첫 번째 해시 값 (Long). Quadratic Probing에서는 사용되지 않음.
 * @param keyHash2 키의 두 번째 해시 값 (Long?). Double Hashing 시 사용됨. null일 경우 예외 발생.
 * @param attempt 현재 탐사 시도 횟수 (Int, 1부터 시작).
 * @param initialIndex 키의 초기 해시 인덱스 (Int).
 * @param capacity 현재 해시 테이블 용량 (Int, 2의 거듭제곱).
 * @return 계산된 다음 탐사 인덱스 (Int).
 */
@OptIn(ExperimentalNativeApi::class)
@CName("probe_next_index")
fun probeNextIndexNative(
    probingType: Int,
    keyHash1: Long,      // 첫 번째 해시는 현재 로직에서 직접 사용 안 함 (initialIndex 계산에 이미 반영됨)
    keyHash2: Long?,     // 두 번째 해시 (Double Hashing 시 사용)
    attempt: Int,        // 시도 횟수 (1 이상)
    initialIndex: Int,   // 초기 인덱스
    capacity: Int,        // 현재 용량
): Int {
    // 입력 값 유효성 검사 (Early return 패턴은 아니지만, 시작 부분에서 검사)
    if (capacity <= 0 || (capacity and (capacity - 1)) != 0) {
        throw IllegalArgumentException("Capacity must be a positive power of two. Got $capacity")
    }
    if (attempt <= 0) {
        throw IllegalArgumentException("Attempt must be positive. Got $attempt")
    }

    val capacityMinus1 = capacity - 1 // 마스크 계산 (Long 타입으로 확장하여 사용)

    when (probingType) {
        PROBING_TYPE_QUADRATIC -> {
            // Quadratic Probing: (initialIndex + (attempt^2 + attempt) / 2) mod capacity
            // (i^2 + i) / 2 계산 시 오버플로우 방지를 위해 Long 타입 사용
            val longAttempt = attempt.toLong()
            val quadraticTerm = (longAttempt * longAttempt + longAttempt) / 2L
            // 최종 인덱스 계산 (Long으로 계산 후 Int로 변환)
            val nextIndexLong = initialIndex.toLong() + quadraticTerm
            // 비트 AND 마스킹으로 모듈러 연산 수행 (capacity가 2의 거듭제곱이므로 가능)
            return (nextIndexLong and capacityMinus1.toLong()).toInt()
        }

        PROBING_TYPE_DOUBLE_HASHING -> {
            // Double Hashing: (initialIndex + attempt * h2) mod capacity
            // keyHash2 null 체크
            if (keyHash2 == null) {
                // Dart FFI에서 Long?를 직접 표현하기 어려우므로, 호출하는 쪽에서
                // Double Hashing 시에는 반드시 유효한 Long 값을 전달해야 함을 의미.
                // 또는 FFI 레벨에서 null을 나타내는 약속된 값(예: 0)을 사용하고 여기서 체크할 수도 있음.
                // 현재는 null 전달 시 예외 발생.
                throw IllegalArgumentException("keyHash2 must be provided and cannot be null for Double Hashing.")
            }
            // h2(k)를 양의 홀수로 만듦: step = abs(h2) | 1
            val step = (abs(keyHash2) or 1L)
            // 최종 인덱스 계산 (Long으로 계산 후 Int로 변환)
            val nextIndexLong = initialIndex.toLong() + attempt.toLong() * step
            // 비트 AND 마스킹으로 모듈러 연산 수행
            return (nextIndexLong and capacityMinus1.toLong()).toInt()
        }

        else -> {
            throw IllegalArgumentException("Unknown probing type: $probingType")
        }
    }
}


// multiplyMod64 함수 (변경 없음)
fun multiplyMod64(a: Long, x: Long, p: Long): Long {
    if (p <= 0L) throw IllegalArgumentException("Modulus p must be positive.")
    if (a == 0L || x == 0L) return 0L
    var currentA = (a % p + p) % p
    var currentX = (x % p + p) % p
    var result = 0L
    while (currentX > 0L) {
        if ((currentX and 1L) == 1L) {
            result = (result + currentA) % p
        }
        currentA = (currentA * 2L) % p
        currentX = currentX shr 1
    }
    return result
}

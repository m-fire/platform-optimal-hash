package io.stormi.support.lang.dart.collection.hash

import kotlinx.cinterop.COpaquePointer
import kotlinx.cinterop.ExperimentalForeignApi
import kotlinx.cinterop.IntVar
import kotlinx.cinterop.get
import kotlinx.cinterop.reinterpret
import kotlin.experimental.ExperimentalNativeApi

// Tabulation Hashing 관련 상수
const val TABLE_SIZE = 1024 // 4 * 256
const val TABLE_BUCKET_SIZE = 256
const val TABLE_COUNT = 4
const val BYTE_SHIFT = 8
const val BYTE_MASK = 0xFF

// Universal Hashing 관련 상수
// 타입을 Long으로 수정하고 값 뒤에 L 추가
const val P_MODULUS: Long = 4294967311L // 소수 모듈러스 p

/**
 * Tabulation Hashing 네이티브 구현.
 */
@OptIn(ExperimentalNativeApi::class, ExperimentalForeignApi::class)
@CName("elastic_tabulation_hash_native")
fun elasticTabulationHashNative(keyHashCode: Long, tableDataPtr: COpaquePointer?): Int {
    if (tableDataPtr == null) {
        return keyHashCode.toInt()
    }
    val tableData = tableDataPtr.reinterpret<IntVar>()
    val h64 = keyHashCode
    val h32 = (h64 shr 32 xor h64).toInt()
    var result = 0
    for (i in 0 until TABLE_COUNT) {
        val byteVal = (h32 shr (i * BYTE_SHIFT)) and BYTE_MASK
        val tableIndex = i * TABLE_BUCKET_SIZE + byteVal
        if (tableIndex < 0 || tableIndex >= TABLE_SIZE) {
            return h32
        }
        result = result xor tableData[tableIndex]
    }
    return result
}

/**
 * Universal Hashing 네이티브 구현 ((ax + b) mod p).
 *
 * @param keyHashCode Dart에서 전달된 64비트 초기 해시 코드 (key.hashCode).
 * @param a Dart에서 생성 및 전달된 파라미터 a (32비트 정수).
 * @param b Dart에서 생성 및 전달된 파라미터 b (32비트 정수).
 * @return 계산된 32비트 Universal 해시 값 ([0, p-1] 범위).
 */
@OptIn(ExperimentalNativeApi::class)
@CName("funnel_universal_hash_native")
fun funnelUniversalHashNative(keyHashCode: Long, a: Int, b: Int): Int {
    val p = P_MODULUS // Long 타입 상수 사용
    // (a * x) mod p 계산 (결과가 Long)
    val axModPLong = multiplyMod64(a.toLong(), keyHashCode, p)

    // (ax + b) mod p 계산 (Long으로 계산)
    var hashValLong = axModPLong + b.toLong() // b를 Long으로 변환하여 덧셈
    hashValLong = (hashValLong % p + p) % p // 최종 결과를 [0, p-1] 범위로 (Long 연산)

    // 최종 결과는 p보다 작으므로 Int로 변환하여 반환
    return hashValLong.toInt()
}


/**
 * 64비트 정수 기반 모듈러 곱셈 헬퍼 함수 ((a * x) % p).
 *
 * @param aIn 곱셈 인자 a (Long 타입).
 * @param xIn 곱셈 인자 x (Long 타입, keyHashCode).
 * @param pIn 모듈러스 p (Long 타입, 양수 가정). <--- 타입 변경
 * @return (a * x) % p 결과 (Long 타입, [0, p-1] 범위). <--- 반환 타입 변경
 */
internal fun multiplyMod64(aIn: Long, xIn: Long, pIn: Long): Long { // <-- 파라미터 및 반환 타입 Long으로 변경
    val p: Long = pIn
    if (p <= 0L) throw IllegalArgumentException("Modulus p must be positive.")
    if (aIn == 0L || xIn == 0L) return 0L

    var currentA = (aIn % p + p) % p
    var currentX = (xIn % p + p) % p
    var result = 0L

    while (currentX > 0L) {
        if ((currentX and 1L) == 1L) {
            result = result + currentA
            if (result >= p) {
                result -= p
            }
        }
        currentA = currentA * 2L
        if (currentA >= p) {
            currentA -= p
        }
        currentX = currentX shr 1
    }
    return result // Long 타입 반환
}

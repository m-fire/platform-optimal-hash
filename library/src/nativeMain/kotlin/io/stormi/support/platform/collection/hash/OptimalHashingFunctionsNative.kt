package io.stormi.support.platform.collection.hash

import kotlinx.cinterop.COpaquePointer
import kotlinx.cinterop.ExperimentalForeignApi
import kotlinx.cinterop.LongVar
import kotlinx.cinterop.get
import kotlinx.cinterop.reinterpret
import kotlin.experimental.ExperimentalNativeApi

// --- Tabulation Hashing 관련 상수 ---
const val TABLE_SIZE = 1024 // 테이블 전체 크기 (4 * 256)
const val TABLE_BUCKET_SIZE = 256 // 각 바이트별 테이블 크기
const val TABLE_COUNT = 4 // 사용하는 바이트 수 (Long 타입은 8바이트지만, 하위 4바이트만 사용)
const val BYTE_SHIFT = 8 // 바이트 이동 시프트 값
const val BYTE_MASK = 0xFF // 바이트 추출 마스크

// --- Universal Hashing 관련 상수 ---
const val P_MODULUS: Long = 4294967311L // 소수 모듈러스 p (2^32에 가까운 소수)

/**
 * Tabulation Hashing 네이티브 구현.
 * 64비트 입력 키의 하위 4바이트를 사용하여 해싱 수행.
 *
 * @param keyHashCode 입력 키의 해시 코드 (64비트 Long).
 * @param tableDataPtr 미리 계산된 랜덤 값 테이블을 가리키는 네이티브 포인터 (`LongVar` 배열).
 * @return 계산된 64비트 해시 값. 테이블 포인터가 null이면 `keyHashCode`를 그대로 반환.
 */
@OptIn(ExperimentalNativeApi::class, ExperimentalForeignApi::class)
@CName("elastic_tabulation_hash") // 네이티브 함수 이름 지정
fun elasticTabulationHashNative(keyHashCode: Long, tableDataPtr: COpaquePointer?): Long {
    // 포인터 유효성 검사 (early return)
    if (tableDataPtr == null) {
        // 테이블 데이터가 없으면 입력값을 그대로 반환 (오류 처리 또는 기본 동작)
        return keyHashCode
    }

    // 포인터를 Long 배열 포인터로 변환 (reinterpret)
    val tableData = tableDataPtr.reinterpret<LongVar>()
    var result = 0L // 최종 해시 결과 (Long)

    // 하위 4개의 바이트에 대해 테이블 조회 및 XOR 연산 수행
    for (i in 0 until TABLE_COUNT) {
        // i번째 바이트 값 추출 (0xFF 마스크 적용)
        val byteVal = (keyHashCode shr (i * BYTE_SHIFT)).toInt() and BYTE_MASK
        // 평탄화된 1차원 테이블에서의 인덱스 계산
        val tableIndex = i * TABLE_BUCKET_SIZE + byteVal

        // 배열 범위 검사 (안전 장치, 이론적으로는 불필요하나 방어적 코드)
        // C Interop 사용 시 메모리 접근 오류 방지를 위해 추가하는 것이 좋음.
        if (tableIndex < 0 || tableIndex >= TABLE_SIZE) {
            // 비정상적인 상황 발생 시 예외 처리
            throw IndexOutOfBoundsException("Table index out of bounds: $tableIndex. Key byte value was $byteVal for byte index $i.")
        }
        // 테이블 값 조회 및 결과에 XOR 누적
        result = result xor tableData[tableIndex]
    }
    return result // 최종 64비트 해시 반환
}

/**
 * Universal Hashing 네이티브 구현 ((a * x + b) mod p).
 * 64비트 연산을 사용하여 결과를 계산.
 *
 * @param keyHashCode 입력 키의 해시 코드 (64비트 Long, x에 해당).
 * @param a 곱셈 인자 (64비트 Long). Universal Hashing에서는 보통 0이 아닌 랜덤 값.
 * @param b 덧셈 인자 (64비트 Long). Universal Hashing에서는 보통 랜덤 값.
 * @return 계산된 64비트 Universal 해시 값 ([0, P_MODULUS - 1] 범위).
 */
@OptIn(ExperimentalNativeApi::class)
@CName("funnel_universal_hash") // 네이티브 함수 이름 지정
fun funnelUniversalHashNative(keyHashCode: Long, a: Long, b: Long): Long {
    // (a * x) mod p 계산 (64비트 모듈러 곱셈 사용)
    val axModPLong = multiplyMod64(a, keyHashCode, P_MODULUS)

    // (ax + b) mod p 계산
    // 덧셈 결과가 음수가 될 수 있으므로, 모듈러 연산 시 p를 더한 후 다시 모듈러 연산 수행
    var hashValLong = axModPLong + b // 64비트 덧셈
    // 최종 결과를 [0, p-1] 범위로 조정
    hashValLong = (hashValLong % P_MODULUS + P_MODULUS) % P_MODULUS

    return hashValLong // 최종 64비트 해시 반환
}


/**
 * 64비트 정수 기반 모듈러 곱셈 헬퍼 함수 ((a * x) % p).
 * 곱셈 결과가 64비트를 초과할 수 있는 경우에도 올바른 모듈러 결과를 계산 (곱셈-및-덧셈 방식 사용).
 *
 * @param a 곱셈 인자 a (Long 타입).
 * @param x 곱셈 인자 x (Long 타입).
 * @param p 모듈러스 p (Long 타입, 양수여야 함).
 * @return (a * x) % p 결과 (Long 타입, [0, p-1] 범위).
 * @throws IllegalArgumentException p가 0 이하일 경우 발생.
 */
fun multiplyMod64(a: Long, x: Long, p: Long): Long {
    // 모듈러스 유효성 검사 (early return)
    if (p <= 0L) throw IllegalArgumentException("Modulus p must be positive.")
    // 0 곱셈 최적화 (early return)
    if (a == 0L || x == 0L) return 0L

    // a와 x를 [0, p-1] 범위로 초기 리덕션 (음수 입력 처리 포함)
    var currentA = (a % p + p) % p
    var currentX = (x % p + p) % p
    var result = 0L // 최종 결과

    // 곱셈-및-덧셈 (Russian Peasant Multiplication 변형) 알고리즘 사용
    // currentX를 비트 단위로 확인하며 계산
    while (currentX > 0L) {
        // currentX의 마지막 비트가 1이면, 현재 currentA 값을 결과에 더함 (모듈러 연산)
        if ((currentX and 1L) == 1L) {
            result = (result + currentA) % p
        }
        // currentA는 2배 증가 (모듈러 연산)
        currentA = (currentA * 2L) % p
        // currentX는 오른쪽으로 1비트 시프트 (정수 나누기 2 효과)
        currentX = currentX shr 1
    }

    return result // 최종 계산된 [0, p-1] 범위의 Long 값 반환
}

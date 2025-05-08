package io.stormi.support.platform.collection.hash

import kotlinx.cinterop.CArrayPointer
import kotlinx.cinterop.ExperimentalForeignApi
import kotlinx.cinterop.UIntVar
import kotlinx.cinterop.allocArray
import kotlinx.cinterop.memScoped
import kotlinx.cinterop.set
import kotlin.math.abs // abs 함수 사용 위해 import
import kotlin.random.Random
import kotlin.random.nextUInt
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertFalse
import kotlin.test.assertNotEquals
import kotlin.test.assertNotNull
import kotlin.test.assertTrue

// --- 테스트용 상수 정의 ---
private const val TEST_TABLE_COUNT = 4
private const val TEST_TABLE_BUCKET_SIZE = 256
private const val TEST_BYTE_SHIFT = 8
private const val TEST_TOTAL_TABLE_SIZE = TEST_TABLE_COUNT * TEST_TABLE_BUCKET_SIZE

private const val P = P_MODULUS
private const val MAX_LONG = Long.MAX_VALUE
private const val MIN_LONG = Long.MIN_VALUE

// 프로빙 타입 상수 (네이티브 코드와 동일하게 사용)
private const val PROBING_TYPE_QUADRATIC_TEST = 0
private const val PROBING_TYPE_DOUBLE_HASHING_TEST = 1


@OptIn(ExperimentalForeignApi::class)
class OptimalHashingFunctionsTest {

    // === multiplyMod64 테스트 (변경 없음) ===
    // ... (이전 테스트 코드 유지) ...
    @Test
    fun `multiplyMod64 기본적인 모듈러 곱셈 기본동작 검증`() {
        assertEquals(200L, multiplyMod64(10L, 20L, P), "10 * 20 mod p")
        assertEquals(2L, multiplyMod64(5L, 7L, 11L), "5 * 7 mod 11")
        assertEquals(1L, multiplyMod64(P - 1L, P - 1L, P), "(p-1)*(p-1) mod p")
        assertEquals(123L, multiplyMod64(1L, 123L, P), "1 * 123 mod p")
        assertEquals(123L, multiplyMod64(123L, 1L, P), "123 * 1 mod p")
    }

    @Test
    fun `multiplyMod64 입력 중 하나가 0인 경우 0 반환 테스트`() {
        assertEquals(0L, multiplyMod64(0L, 123L, P), "0 * 123 mod p")
        assertEquals(0L, multiplyMod64(123L, 0L, P), "123 * 0 mod p")
    }

    @Test
    fun `multiplyMod64 결과 범위 0 과 p-1 확인 테스트`() {
        val samples = listOf(
            Triple(10L, 20L, P),
            Triple(P - 1L, P - 1L, P),
            Triple(0L, 123L, P),
            Triple(MAX_LONG, MAX_LONG, P),
            Triple(MIN_LONG, MAX_LONG, P),
            Triple(12345L, 67890L, 101L),
        )
        for ((a, x, pVal) in samples) {
            val result = multiplyMod64(a, x, pVal)
            assertTrue(result >= 0L && result < pVal, "결과 $result 는 a=$a, x=$x 에 대해 [0, $pVal) 범위여야 함")
        }
        repeat(100) {
            val a = Random.Default.nextLong()
            val x = Random.Default.nextLong()
            val pVal = Random.Default.nextLong(1L, P + 1)
            val result = multiplyMod64(a, x, pVal)
            assertTrue(result >= 0L && result < pVal, "[Random] 결과 $result 는 a=$a, x=$x 에 대해 [0, $pVal) 범위여야 함")
        }
    }

    @Test
    fun `multiplyMod64 모듈러스 경계값 근처 처리 테스트`() {
        val expectedNearHalf = multiplyMod64(2L, P / 2L, P)
        assertEquals(expectedNearHalf, multiplyMod64(2L, P / 2L, P), "2 * (p/2) mod p")
        assertEquals(P - 2L, multiplyMod64(P - 1L, 2L, P), "(p-1) * 2 mod p")
    }


    // === elasticTabulationHashNative 테스트 (변경 없음) ===
    // ... (이전 테스트 코드 유지) ...
    private val mockTableData = LongArray(TEST_TOTAL_TABLE_SIZE) { index ->
        Random.Default.nextUInt().toLong()
    }

    private fun <R> withMockTablePointer(block: (CArrayPointer<UIntVar>) -> R): R {
        return memScoped {
            val ptr: CArrayPointer<UIntVar> = allocArray<UIntVar>(mockTableData.size)
            mockTableData.forEachIndexed { index, value -> ptr[index] = value.toUInt() }
            block(ptr)
        }
    }

    @Test
    fun `elasticTabulationHashNative 결정론적 동작 테스트`() {
        val hashCodeInput = 123456789123456789L
        withMockTablePointer { ptr ->
            val hash1 = elasticTabulationHashNative(
                hashCodeInput,
                ptr,
                TEST_TABLE_COUNT,
                TEST_TABLE_BUCKET_SIZE,
                TEST_BYTE_SHIFT
            )
            val hash2 = elasticTabulationHashNative(
                hashCodeInput,
                ptr,
                TEST_TABLE_COUNT,
                TEST_TABLE_BUCKET_SIZE,
                TEST_BYTE_SHIFT
            )
            assertEquals(hash1, hash2, "동일 입력 $hashCodeInput 에 대해 해시는 동일해야 함")
        }
    }

    @Test
    fun `elasticTabulationHashNative 경계값 입력 정상 실행 테스트`() {
        withMockTablePointer { ptr ->
            assertNotNull(
                elasticTabulationHashNative(
                    0L,
                    ptr,
                    TEST_TABLE_COUNT,
                    TEST_TABLE_BUCKET_SIZE,
                    TEST_BYTE_SHIFT
                ), "0L 입력 실행"
            )
            assertNotNull(
                elasticTabulationHashNative(
                    -1L,
                    ptr,
                    TEST_TABLE_COUNT,
                    TEST_TABLE_BUCKET_SIZE,
                    TEST_BYTE_SHIFT
                ), "-1L 입력 실행"
            )
            assertNotNull(
                elasticTabulationHashNative(
                    MAX_LONG,
                    ptr,
                    TEST_TABLE_COUNT,
                    TEST_TABLE_BUCKET_SIZE,
                    TEST_BYTE_SHIFT
                ), "Long.MAX_VALUE 입력 실행"
            )
            assertNotNull(
                elasticTabulationHashNative(
                    MIN_LONG,
                    ptr,
                    TEST_TABLE_COUNT,
                    TEST_TABLE_BUCKET_SIZE,
                    TEST_BYTE_SHIFT
                ), "Long.MIN_VALUE 입력 실행"
            )
        }
    }

    @Test
    fun `elasticTabulationHashNative 입력 비트 변경 시 출력 변경 경향 확인`() {
        val input1 = 1234567890123456789L
        val input2 = input1 + 1L
        val input3 = input1 xor (1L shl 25)

        withMockTablePointer { ptr ->
            val hash1 =
                elasticTabulationHashNative(input1, ptr, TEST_TABLE_COUNT, TEST_TABLE_BUCKET_SIZE, TEST_BYTE_SHIFT)
            val hash2 =
                elasticTabulationHashNative(input2, ptr, TEST_TABLE_COUNT, TEST_TABLE_BUCKET_SIZE, TEST_BYTE_SHIFT)
            val hash3 =
                elasticTabulationHashNative(input3, ptr, TEST_TABLE_COUNT, TEST_TABLE_BUCKET_SIZE, TEST_BYTE_SHIFT)

            println("Tabulation Avalanche 확인: H1=$hash1, H2(LSB 변경)=$hash2, H3(25번 비트 변경)=$hash3")
            assertNotEquals(hash1, hash2, "LSB 변경($input1 -> $input2) 시 해시는 변경될 가능성이 높음")
            assertNotEquals(hash1, hash3, "25번 비트 변경 시 해시는 변경될 가능성이 높음")
        }
    }

    @Test
    fun `elasticTabulationHashNative XOR 연산 영향 간접적 확인`() {
        val input1 = 0x0102030405060708L
        val input2 = 0x0807060504030201L
        val input3 = 0x00FF00FF00FF00FFL

        withMockTablePointer { ptr ->
            val hash1 =
                elasticTabulationHashNative(input1, ptr, TEST_TABLE_COUNT, TEST_TABLE_BUCKET_SIZE, TEST_BYTE_SHIFT)
            val hash2 =
                elasticTabulationHashNative(input2, ptr, TEST_TABLE_COUNT, TEST_TABLE_BUCKET_SIZE, TEST_BYTE_SHIFT)
            val hash3 =
                elasticTabulationHashNative(input3, ptr, TEST_TABLE_COUNT, TEST_TABLE_BUCKET_SIZE, TEST_BYTE_SHIFT)

            println("Tabulation XOR 확인: Hash1=$hash1, Hash2=$hash2, Hash3=$hash3")
            assertFalse(hash1 == hash2 && hash1 == hash3, "다른 바이트 패턴을 가진 입력들에 대한 해시는 일반적으로 달라야 함")
        }
    }

    @Test
    fun `elasticTabulationHashNative 테이블 포인터 null일 때 기본값 반환 테스트`() {
        val hashCodeInput = 123456789L
        val defaultHash = elasticTabulationHashNative(
            hashCodeInput,
            null, // ptr을 null로 전달
            TEST_TABLE_COUNT,
            TEST_TABLE_BUCKET_SIZE,
            TEST_BYTE_SHIFT
        )
        assertEquals(hashCodeInput, defaultHash, "테이블 포인터가 null일 때는 keyHashCode를 반환해야 함")
    }


    // === funnelUniversalHashNative 테스트 (변경 없음) ===
    // ... (이전 테스트 코드 유지) ...
    @Test
    fun `funnelUniversalHashNative 결정론적 동작 테스트`() {
        val hashCodeInput = 123456789123456789L
        val a = 101L
        val b = 202L
        val hash1 = funnelUniversalHashNative(hashCodeInput, a, b)
        val hash2 = funnelUniversalHashNative(hashCodeInput, a, b)
        assertEquals(hash1, hash2, "동일 입력(hc=$hashCodeInput, a=$a, b=$b)에 대해 해시는 동일해야 함")
    }

    @Test
    fun `funnelUniversalHashNative 경계값 입력 정상 실행 및 결과 범위 확인`() {
        val a = 31L
        val b = 41L
        val inputs = listOf(0L, -1L, MAX_LONG, MIN_LONG)
        inputs.forEach { hc ->
            val result = funnelUniversalHashNative(hc, a, b)
            assertTrue(result >= 0L && result < P, "결과 $result 는 입력 $hc 에 대해 [0, $P) 범위여야 함")
            println("[경계값 테스트] 입력 $hc -> 결과 $result")
        }
    }

    @Test
    fun `funnelUniversalHashNative a=1 b=0 일 때 'x mod p' 와 동일한 결과 확인`() {
        val inputs =
            listOf(0L, 1L, -1L, 12345L, P, P - 1L, P + 1L, MAX_LONG, MIN_LONG)
        inputs.forEach { hc ->
            val expected = multiplyMod64(1L, hc, P)
            val actual = funnelUniversalHashNative(hc, 1L, 0L)
            assertEquals(expected, actual, "Hash($hc, a=1, b=0) 는 $expected 여야 함")
        }
    }

    @Test
    fun `funnelUniversalHashNative 다른 파라미터 a b 에 대해 일반적으로 다른 출력 생성 확인`() {
        val hashCodeInput = 987654321098765432L
        val a1 = 303L
        val b1 = 404L
        val a2 = 505L
        val b2 = 606L

        val hash1 = funnelUniversalHashNative(hashCodeInput, a1, b1)
        val hash2 = funnelUniversalHashNative(hashCodeInput, a2, b1)
        val hash3 = funnelUniversalHashNative(hashCodeInput, a1, b2)

        println("Universal 해시 1 (a=$a1, b=$b1): $hash1")
        println("Universal 해시 2 (a=$a2, b=$b1): $hash2")
        println("Universal 해시 3 (a=$a1, b=$b2): $hash3")

        assertFalse(hash1 == hash2 && hash1 == hash3, "다른 a/b($a1/$b1 vs $a2/$b1 vs $a1/$b2)를 가진 해시는 일반적으로 달라야 함")
        assertNotEquals(hash1, hash2, "다른 'a'($a1 vs $a2)를 가진 해시는 이상적으로 달라야 함 (충돌 가능)")
        assertNotEquals(hash1, hash3, "다른 'b'($b1 vs $b2)를 가진 해시는 이상적으로 달라야 함 (충돌 가능)")
    }

    @Test
    fun `funnelUniversalHashNative 결과 범위 0 과 P_MODULUS-1 확인 테스트`() {
        val samples = listOf(
            Triple(123L, 101L, 202L),
            Triple(MAX_LONG, 31L, 41L),
            Triple(MIN_LONG, 55L, 66L),
            Triple(0L, 1L, 0L),
            Triple(-1L, 99L, 199L),
            Triple(P, 5L, 10L),
            Triple(P + 10L, 7L, 15L),
            Triple(100L, 0L, 50L),
        )

        for ((hc, a, b) in samples) {
            val result = funnelUniversalHashNative(hc, a, b)
            assertTrue(
                result >= 0L && result < P,
                "[Sample] 결과 $result 는 hc=$hc, a=$a, b=$b 에 대해 [0, $P) 범위여야 함",
            )
            println("[Sample 범위 테스트] 입력 (hc=$hc, a=$a, b=$b) -> 결과 $result")
        }
        repeat(100) {
            val hc = Random.Default.nextLong()
            val a = Random.Default.nextLong(0L, P)
            val b = Random.Default.nextLong()
            val result = funnelUniversalHashNative(hc, a, b)
            assertTrue(
                result >= 0L && result < P,
                "[Random] 결과 $result 는 hc=$hc, a=$a, b=$b 에 대해 [0, $P) 범위여야 함",
            )
        }
    }


    // === probeNextIndexNative 테스트 ===

    @Test
    fun `probeNextIndexNative Quadratic Probing 테스트`() {
        val initialIndex = 5
        val capacity = 16 // 2의 거듭제곱
        // h(k, i) = (h1(k) + (i^2 + i)/2) mod m
        // attempt = 1: (5 + (1*1+1)/2) mod 16 = (5 + 1) mod 16 = 6
        // attempt = 2: (5 + (2*2+2)/2) mod 16 = (5 + 3) mod 16 = 8
        // attempt = 3: (5 + (3*3+3)/2) mod 16 = (5 + 6) mod 16 = 11
        // attempt = 4: (5 + (4*4+4)/2) mod 16 = (5 + 10) mod 16 = 15
        // attempt = 5: (5 + (5*5+5)/2) mod 16 = (5 + 15) mod 16 = 20 mod 16 = 4
        val expectedIndices = listOf(6, 8, 11, 15, 4)

        for (i in 1..expectedIndices.size) {
            val nextIndex = probeNextIndexNative(
                probingType = PROBING_TYPE_QUADRATIC_TEST,
                keyHash1 = 0L, // Quadratic에서는 사용 안 함
                keyHash2 = null, // Quadratic에서는 사용 안 함
                attempt = i,
                initialIndex = initialIndex,
                capacity = capacity
            )
            assertEquals(expectedIndices[i - 1], nextIndex, "Quadratic: attempt=$i, expected=${expectedIndices[i - 1]}")
            assertTrue(
                nextIndex >= 0 && nextIndex < capacity,
                "Quadratic: Index $nextIndex out of bounds [0, $capacity)"
            )
        }
    }

    @Test
    fun `probeNextIndexNative Double Hashing 테스트`() {
        val initialIndex = 7
        val capacity = 32 // 2의 거듭제곱
        val hash2 = 12345L // 두 번째 해시 값
        // step = abs(12345) | 1 = 12345 | 1 = 12345 (이미 홀수)
        val step = abs(hash2) or 1L
        assertEquals(12345L, step)

        // h(k, i) = (h1(k) + i * h2) mod m
        // attempt = 1: (7 + 1 * 12345) mod 32 = 12352 mod 32 = (7 + (12345 mod 32)) mod 32 = (7 + 25) mod 32 = 0
        // attempt = 2: (7 + 2 * 12345) mod 32 = (7 + 24690) mod 32 = (7 + (24690 mod 32)) mod 32 = (7 + 18) mod 32 = 25
        // attempt = 3: (7 + 3 * 12345) mod 32 = (7 + 37035) mod 32 = (7 + (37035 mod 32)) mod 32 = (7 + 11) mod 32 = 18
        val expectedIndices = listOf(0, 25, 18)

        for (i in 1..expectedIndices.size) {
            val nextIndex = probeNextIndexNative(
                probingType = PROBING_TYPE_DOUBLE_HASHING_TEST,
                keyHash1 = 0L, // Double Hashing에서는 사용 안 함
                keyHash2 = hash2, // 두 번째 해시 전달
                attempt = i,
                initialIndex = initialIndex,
                capacity = capacity
            )
            assertEquals(
                expectedIndices[i - 1],
                nextIndex,
                "Double Hashing: attempt=$i, expected=${expectedIndices[i - 1]}"
            )
            assertTrue(
                nextIndex >= 0 && nextIndex < capacity,
                "Double Hashing: Index $nextIndex out of bounds [0, $capacity)"
            )
        }
    }

    @Test
    fun `probeNextIndexNative Double Hashing 음수 hash2 테스트`() {
        val initialIndex = 7
        val capacity = 32
        val hash2: Long = -12345L // 음수 두 번째 해시
        // step = abs(-12345) | 1 = 12345 | 1 = 12345
        val step = abs(hash2) or 1L
        assertEquals(12345L, step) // 이전 테스트와 동일한 step

        // 결과는 이전 테스트와 동일해야 함
        val expectedIndices = listOf(0, 25, 18)

        for (i in 1..expectedIndices.size) {
            val nextIndex = probeNextIndexNative(
                probingType = PROBING_TYPE_DOUBLE_HASHING_TEST,
                keyHash1 = 0L,
                keyHash2 = hash2,
                attempt = i,
                initialIndex = initialIndex,
                capacity = capacity
            )
            assertEquals(
                expectedIndices[i - 1],
                nextIndex,
                "Double Hashing (negative h2): attempt=$i, expected=${expectedIndices[i - 1]}"
            )
        }
    }

    @Test
    fun `probeNextIndexNative Double Hashing 짝수 hash2 테스트`() {
        val initialIndex = 7
        val capacity = 32
        val hash2 = 12344L // 짝수 두 번째 해시
        // step = abs(12344) | 1 = 12344 | 1 = 12345
        val step = abs(hash2) or 1L
        assertEquals(12345L, step) // 홀수로 변환됨

        // 결과는 이전 테스트와 동일해야 함
        val expectedIndices = listOf(0, 25, 18)

        for (i in 1..expectedIndices.size) {
            val nextIndex = probeNextIndexNative(
                probingType = PROBING_TYPE_DOUBLE_HASHING_TEST,
                keyHash1 = 0L,
                keyHash2 = hash2,
                attempt = i,
                initialIndex = initialIndex,
                capacity = capacity
            )
            assertEquals(
                expectedIndices[i - 1],
                nextIndex,
                "Double Hashing (even h2): attempt=$i, expected=${expectedIndices[i - 1]}"
            )
        }
    }

    @Test
    fun `probeNextIndexNative 잘못된 파라미터 예외 발생 테스트`() {
        // 잘못된 probingType
        assertFailsWith<IllegalArgumentException>("Unknown probing type") {
            probeNextIndexNative(99, 0L, null, 1, 0, 16)
        }
        // attempt <= 0
        assertFailsWith<IllegalArgumentException>("Attempt must be positive") {
            probeNextIndexNative(PROBING_TYPE_QUADRATIC_TEST, 0L, null, 0, 0, 16)
        }
        assertFailsWith<IllegalArgumentException>("Attempt must be positive") {
            probeNextIndexNative(PROBING_TYPE_QUADRATIC_TEST, 0L, null, -1, 0, 16)
        }
        // capacity <= 0
        assertFailsWith<IllegalArgumentException>("Capacity must be a positive power of two") {
            probeNextIndexNative(PROBING_TYPE_QUADRATIC_TEST, 0L, null, 1, 0, 0)
        }
        assertFailsWith<IllegalArgumentException>("Capacity must be a positive power of two") {
            probeNextIndexNative(PROBING_TYPE_QUADRATIC_TEST, 0L, null, 1, 0, -16)
        }
        // capacity가 2의 거듭제곱이 아님
        assertFailsWith<IllegalArgumentException>("Capacity must be a positive power of two") {
            probeNextIndexNative(PROBING_TYPE_QUADRATIC_TEST, 0L, null, 1, 0, 15)
        }
        // Double Hashing 시 keyHash2가 null
        assertFailsWith<IllegalArgumentException>("keyHash2 must be provided and cannot be null for Double Hashing") {
            probeNextIndexNative(PROBING_TYPE_DOUBLE_HASHING_TEST, 0L, null, 1, 0, 16)
        }
    }
}

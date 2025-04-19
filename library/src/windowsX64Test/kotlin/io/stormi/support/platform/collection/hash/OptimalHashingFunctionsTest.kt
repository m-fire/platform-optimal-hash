package io.stormi.support.platform.collection.hash

import kotlinx.cinterop.CArrayPointer
import kotlinx.cinterop.ExperimentalForeignApi
import kotlinx.cinterop.IntVar
import kotlinx.cinterop.allocArray
import kotlinx.cinterop.memScoped
import kotlinx.cinterop.set
import kotlin.random.Random
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertNotEquals
import kotlin.test.assertNotNull
import kotlin.test.assertTrue

@OptIn(ExperimentalForeignApi::class)
class OptimalHashingFunctionsTest {

    // ElasticTabulationHasher 테스트용 모의 테이블 데이터. 모든 요소가 다른 값을 가지도록 수정 (XOR 테스트 용이성).
    private val mockTableData = IntArray(1024) { index ->
        // 고유한 값을 보장하는 간단한 패턴 (예시)
        val base = index * 31 + (index % 7) * 13
        base xor (base shr 16) // 비트 연산 추가
    }

    // === multiplyMod64 테스트 ===

    @Test
    fun `multiplyMod64 기본적인 모듈러 곱셈 테스트`() {
        // 기본적인 모듈러 곱셈 테스트
        assertEquals(200L, multiplyMod64(10L, 20L, P_MODULUS), "10 * 20 mod p")
        assertEquals(2L, multiplyMod64(5L, 7L, 11L), "5 * 7 mod 11")
        assertEquals(
            1L,
            multiplyMod64(P_MODULUS - 1L, P_MODULUS - 1L, P_MODULUS),
            "(p-1)*(p-1) mod p",
        )
        assertEquals(123L, multiplyMod64(1L, 123L, P_MODULUS), "1 * 123 mod p")
        assertEquals(123L, multiplyMod64(123L, 1L, P_MODULUS), "123 * 1 mod p")
    }

    @Test
    fun `multiplyMod64 입력 중 하나가 0인 경우 0 반환 테스트`() {
        // 입력 중 하나가 0인 경우 테스트
        assertEquals(0L, multiplyMod64(0L, 123L, P_MODULUS), "0 * 123 mod p")
        assertEquals(0L, multiplyMod64(123L, 0L, P_MODULUS), "123 * 0 mod p")
    }

    @Test
    fun `multiplyMod64 결과 범위 0 과 p-1 확인 테스트`() {
        // 샘플 값을 사용하여 결과가 항상 [0, p-1] 범위인지 확인
        val samples = listOf(
            Triple(10L, 20L, P_MODULUS),
            Triple(P_MODULUS - 1L, P_MODULUS - 1L, P_MODULUS),
            Triple(0L, 123L, P_MODULUS),
            Triple(Long.MAX_VALUE, Long.MAX_VALUE, P_MODULUS), // 큰 값
            Triple(Long.MIN_VALUE, Long.MAX_VALUE, P_MODULUS), // 부호 혼합 (모듈로 처리)
            Triple(12345L, 67890L, 101L), // 작은 모듈러스
        )

        for ((a, x, p) in samples) {
            val result = multiplyMod64(a, x, p)
            assertTrue(result >= 0L && result < p, "결과 $result 는 a=$a, x=$x 에 대해 [0, $p) 범위여야 함")
        }

        // 무작위 값으로 테스트 (제한된 프로퍼티 테스트 시뮬레이션)
        repeat(100) {
            val a = Random.Default.nextLong()
            val x = Random.Default.nextLong()
            // 모듈러스 p가 양수이고 테스트에 적합한 크기인지 확인
            val p = Random.Default.nextLong(1L, Long.MAX_VALUE / 2) // 테스트 생성 시 오버플로 문제 방지
            val result = multiplyMod64(a, x, p)
            assertTrue(result >= 0L && result < p, "[Random] 결과 $result 는 a=$a, x=$x 에 대해 [0, $p) 범위여야 함")
        }
    }

    @Test
    fun `multiplyMod64 모듈러스 경계값 근처 처리 테스트`() {
        // 모듈러스 경계값 근처 테스트
        val expectedNearHalf = (P_MODULUS - (P_MODULUS % 2L)) % P_MODULUS // 2 * (p/2) 예상값
        assertEquals(
            expectedNearHalf,
            multiplyMod64(2L, P_MODULUS / 2L, P_MODULUS),
            "2 * (p/2) mod p",
        )
        assertEquals(
            P_MODULUS - 2L,
            multiplyMod64(P_MODULUS - 1L, 2L, P_MODULUS),
            "(p-1) * 2 mod p",
        )
    }


    // === elasticTabulationHashNative 테스트 ===

    // 테스트를 위해 memScoped 내에서 CArrayPointer를 생성하는 헬퍼
    @OptIn(ExperimentalForeignApi::class)
    private fun <R> withMockTablePointer(block: (CArrayPointer<IntVar>) -> R): R {
        return memScoped {
            val ptr: CArrayPointer<IntVar> = allocArray<IntVar>(mockTableData.size)
            mockTableData.forEachIndexed { index, value -> ptr[index] = value }
            block(ptr)
        }
    }

    @Test
    fun `elasticTabulationHashNative 결정론적 동작 테스트`() {
        // 함수가 결정론적인지 테스트 (동일 입력 -> 동일 출력)
        val hashCodeInput = 123456789123456789L
        withMockTablePointer { ptr ->
            val hash1 = elasticTabulationHashNative(hashCodeInput, ptr)
            val hash2 = elasticTabulationHashNative(hashCodeInput, ptr)
            assertEquals(hash1, hash2, "동일 입력에 대해 해시는 동일해야 함")
        }
    }

    @Test
    fun `elasticTabulationHashNative 경계값 입력 정상 실행 테스트`() {
        // 경계값 입력(0, -1, MAX, MIN)으로 실행 테스트
        withMockTablePointer { ptr ->
            // 예외 없이 실행되는지만 확인
            assertNotNull(elasticTabulationHashNative(0L, ptr), "0L에 대한 해시")
            assertNotNull(elasticTabulationHashNative(-1L, ptr), "-1L에 대한 해시")
            assertNotNull(elasticTabulationHashNative(Long.MAX_VALUE, ptr), "Long.MAX_VALUE에 대한 해시")
            assertNotNull(elasticTabulationHashNative(Long.MIN_VALUE, ptr), "Long.MIN_VALUE에 대한 해시")
        }
    }

    @Test
    fun `elasticTabulationHashNative 입력 비트 변경 시 출력 변경 경향 Avalanche Effect 간접 확인`() {
        // 입력 비트 변경 시 출력 변경 경향 확인 (Avalanche Effect 간접 확인)
        val input1 = 1234567890123456789L // 예시 값
        val input2 = input1 + 1L // LSB 변경
        val input3 = input1 xor (1L shl 10) // 중간 비트 변경

        withMockTablePointer { ptr ->
            val hash1 = elasticTabulationHashNative(input1, ptr)
            val hash2 = elasticTabulationHashNative(input2, ptr)
            val hash3 = elasticTabulationHashNative(input3, ptr)

            println("테뷸레이션 Avalanche 확인: H1=$hash1, H2(LSB 변경)=$hash2, H3(10번 비트 변경)=$hash3")
            assertNotEquals(hash1, hash2, "LSB 변경 시 해시는 변경될 가능성이 높음")
            assertNotEquals(hash1, hash3, "10번 비트 변경 시 해시는 변경될 가능성이 높음")
        }
    }

    @Test
    fun `elasticTabulationHashNative XOR-Folding 영향 간접적 확인`() {
        // XOR-Folding 영향 확인 (간접적)
        // h64 와 h64 + (1L shl 32) 는 하위 32비트는 같고 상위 32비트만 다름.
        // 테이블이 잘 분산되어 있다면 XOR-Folding 결과는 달라야 함.
        val inputBase = 1234567890L
        val inputHighBit = inputBase + (1L shl 32) // 상위 32비트에 1 추가

        withMockTablePointer { ptr ->
            val hashBase = elasticTabulationHashNative(inputBase, ptr)
            val hashHigh = elasticTabulationHashNative(inputHighBit, ptr)

            println("테뷸레이션 XOR-Fold 확인: BaseHash=$hashBase, HighBitHash=$hashHigh")
            // 테이블 값이 다양하다면 결과는 달라야 함.
            assertNotEquals(hashBase, hashHigh, "다른 상위 비트와의 XOR-folding으로 인해 해시가 달라야 함")
        }
    }

    @Test
    fun `elasticTabulationHashNative 테이블 포인터 null일 때 기본값 반환 테스트`() {
        // 테이블 포인터가 null일 때 기본값 반환 테스트
        val hashCodeInput = 123L
        val defaultHash = elasticTabulationHashNative(hashCodeInput, null)
        // 예상되는 기본 동작(예: hashCode.toInt())과 비교 확인
        assertEquals(hashCodeInput.toInt(), defaultHash, "테이블이 null일 때 기본 해시를 반환해야 함")
    }


    // === funnelUniversalHashNative 테스트 ===

    @Test
    fun `funnelUniversalHashNative 결정론적 동작 테스트`() {
        // 함수가 결정론적인지 테스트
        val hashCodeInput = 123456789123456789L
        val a = 101
        val b = 202
        val hash1 = funnelUniversalHashNative(hashCodeInput, a, b)
        val hash2 = funnelUniversalHashNative(hashCodeInput, a, b)
        assertEquals(hash1, hash2, "동일 입력 및 파라미터에 대해 해시는 동일해야 함")
    }

    @Test
    fun `funnelUniversalHashNative 경계값 입력 정상 실행 및 결과 범위 확인`() {
        val a = 31
        val b = 41
        val p = P_MODULUS

        val inputs = listOf(0L, -1L, Long.MAX_VALUE, Long.MIN_VALUE)
        inputs.forEach { hc ->
            val result = funnelUniversalHashNative(hc, a, b)
            val unsignedResult = result.toLong() and 0xFFFFFFFFL
            assertTrue(unsignedResult in 0 until p, "입력 $hc 에 대한 결과 $unsignedResult 는 [0, $p) 범위여야 함")
        }
    }

    @Test
    fun `funnelUniversalHashNative a=1 b=0 일 때 'x mod p' 와 유사한 결과 확인`() {
        // a=1, b=0 일 때 (x mod p) 와 유사한 결과 확인
        val inputs = listOf(0L, 1L, -1L, 12345L, P_MODULUS, P_MODULUS - 1L, P_MODULUS + 1L, Long.MAX_VALUE)
        inputs.forEach { hc ->
            // 예상 결과 계산: (1 * hc + 0) mod P_MODULUS
            val expected = multiplyMod64(1L, hc, P_MODULUS).toInt()
            val actual = funnelUniversalHashNative(hc, 1, 0)
            assertEquals(expected, actual, "Hash($hc, a=1, b=0) 는 ${hc % P_MODULUS} 여야 함")
        }
    }

    @Test
    fun `funnelUniversalHashNative 다른 파라미터 a b 에 대해 일반적으로 다른 출력 생성 확인`() {
        // 다른 파라미터 a, b에 대해 일반적으로 다른 출력 생성 확인
        val hashCodeInput = 987654321L
        val a1 = 303
        val b1 = 404
        val a2 = 505 // 다른 'a'
        val b2 = 606 // 다른 'b'

        val hash1 = funnelUniversalHashNative(hashCodeInput, a1, b1)
        val hash2 = funnelUniversalHashNative(hashCodeInput, a2, b1) // a 다름
        val hash3 = funnelUniversalHashNative(hashCodeInput, a1, b2) // b 다름

        println("유니버설 해시 1 (a=$a1, b=$b1): $hash1")
        println("유니버설 해시 2 (a=$a2, b=$b1): $hash2")
        println("유니버설 해시 3 (a=$a1, b=$b2): $hash3")

        // 세 해시가 모두 같을 가능성은 낮다고 단언 (충돌은 가능하지만 모두 같을 가능성은 낮음)
        assertFalse(hash1 == hash2 && hash1 == hash3, "다른 a/b를 가진 해시는 일반적으로 달라야 함")
        // 개별 비교는 해시 함수의 예상된 동작인 충돌로 인해 실패할 수 있음
        assertNotEquals(hash1, hash2, "다른 'a'를 가진 해시는 이상적으로 달라야 함 (충돌 가능)")
        assertNotEquals(hash1, hash3, "다른 'b'를 가진 해시는 이상적으로 달라야 함 (충돌 가능)")
    }

    @Test
    fun `funnelUniversalHashNative 결과 범위 0 과 p-1 확인 테스트`() {
        // 샘플 값을 사용하여 결과가 항상 [0, p-1] 범위인지 확인
        val samples = listOf(
            Triple(123L, 101, 202),
            Triple(Long.MAX_VALUE, 31, 41),
            Triple(Long.MIN_VALUE, 55, 66),
            Triple(0L, 1, 0),
            Triple(-1L, 99, 199),
        )
        val pLong = P_MODULUS

        for ((hc, a, b) in samples) {
            val validA = if (a == 0) 1 else a
            val result = funnelUniversalHashNative(hc, validA, b)
            val unsignedResult = result.toLong() and 0xFFFFFFFFL
            assertTrue(
                unsignedResult in 0 until pLong,
                "[Unsigned] 결과 $unsignedResult 는 hc=$hc, a=$validA, b=$b 에 대해 [0, $pLong) 범위여야 함"
            )
        }

        // 무작위 값으로 테스트 (제한된 프로퍼티 테스트 시뮬레이션)
        repeat(100) {
            val hc = Random.Default.nextLong()
            val a = Random.Default.nextInt(1, Int.MAX_VALUE)
            val b = Random.Default.nextInt()
            val result = funnelUniversalHashNative(hc, a, b)
            val unsignedResult = result.toLong() and 0xFFFFFFFFL
            assertTrue(
                unsignedResult in 0 until pLong,
                "[Random][Unsigned] 결과 $unsignedResult 는 hc=$hc, a=$a, b=$b 에 대해 [0, $pLong) 범위여야 함"
            )
        }
    }
}

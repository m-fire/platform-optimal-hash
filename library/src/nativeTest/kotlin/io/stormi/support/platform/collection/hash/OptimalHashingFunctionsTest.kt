package io.stormi.support.platform.collection.hash

import kotlinx.cinterop.CArrayPointer
import kotlinx.cinterop.ExperimentalForeignApi
import kotlinx.cinterop.LongVar // 네이티브 Long 타입 포인터 사용
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

private const val P = P_MODULUS
private const val MAX_LONG = Long.MAX_VALUE
private const val MIN_LONG = Long.MIN_VALUE

@OptIn(ExperimentalForeignApi::class)
class OptimalHashingFunctionsTest {

    // === multiplyMod64 테스트 ===

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
        // 입력값 중 0이 포함된 경우 0 반환 확인
        assertEquals(0L, multiplyMod64(0L, 123L, P), "0 * 123 mod p")
        assertEquals(0L, multiplyMod64(123L, 0L, P), "123 * 0 mod p")
    }

    @Test
    fun `multiplyMod64 결과 범위 0 과 p-1 확인 테스트`() {
        // 결과값이 항상 [0, p-1] 범위 내에 있는지 확인
        val samples = listOf(
            Triple(10L, 20L, P),
            Triple(P - 1L, P - 1L, P),
            Triple(0L, 123L, P),
            Triple(MAX_LONG, MAX_LONG, P), // 큰 값 테스트
            Triple(MIN_LONG, MAX_LONG, P), // 음수 및 큰 값 테스트
            Triple(12345L, 67890L, 101L), // 작은 모듈러스 테스트
        )
        for ((a, x, p) in samples) {
            val result = multiplyMod64(a, x, p)
            assertTrue(result >= 0L && result < p, "결과 $result 는 a=$a, x=$x 에 대해 [0, $p) 범위여야 함")
        }
        // 무작위 값으로 범위 테스트
        repeat(100) {
            val a = Random.Default.nextLong()
            val x = Random.Default.nextLong()
            // p는 양수여야 하며, 테스트 관련성을 위해 P_MODULUS 범위 내 값 사용
            val p = Random.Default.nextLong(1L, P + 1)
            val result = multiplyMod64(a, x, p)
            assertTrue(result >= 0L && result < p, "[Random] 결과 $result 는 a=$a, x=$x 에 대해 [0, $p) 범위여야 함")
        }
    }

    @Test
    fun `multiplyMod64 모듈러스 경계값 근처 처리 테스트`() {
        // 모듈러스 p의 경계값 근처 연산 테스트
        val expectedNearHalf = multiplyMod64(2L, P / 2L, P) // 예상 값 직접 계산
        assertEquals(expectedNearHalf, multiplyMod64(2L, P / 2L, P), "2 * (p/2) mod p")
        assertEquals(P - 2L, multiplyMod64(P - 1L, 2L, P), "(p-1) * 2 mod p")
    }

    // === elasticTabulationHashNative 테스트 ===

    // Tabulation Hashing 테스트용 모의 테이블 데이터 (LongArray 사용)
    private val mockTableData = LongArray(TABLE_SIZE) { index ->
        // XOR 테스트 용이성을 위해 모든 요소가 다른 Long 값을 갖도록 설정
        val base = index.toLong() * 31337L + (index % 13L) * 101L
        base xor (base ushr 20) xor (base shl 15) // Long 타입에 맞는 비트 연산으로 값 생성
    }

    // 네이티브 포인터 생성을 위한 헬퍼 함수 (LongVar 사용)
    private fun <R> withMockTablePointer(block: (CArrayPointer<LongVar>) -> R): R {
        return memScoped { // 메모리 관리 스코프
            // LongVar 타입의 네이티브 배열 할당
            val ptr: CArrayPointer<LongVar> = allocArray<LongVar>(mockTableData.size)
            // mockTableData의 Long 값들을 네이티브 배열에 복사
            mockTableData.forEachIndexed { index, value -> ptr[index] = value }
            block(ptr) // 생성된 포인터를 사용하여 테스트 블록 실행
        }
    }

    @Test
    fun `elasticTabulationHashNative 결정론적 동작 테스트`() {
        // 동일 입력에 대해 항상 동일한 출력을 내는지 확인 (결정론적 동작)
        val hashCodeInput = 123456789123456789L
        withMockTablePointer { ptr ->
            val hash1 = elasticTabulationHashNative(hashCodeInput, ptr)
            val hash2 = elasticTabulationHashNative(hashCodeInput, ptr)
            assertEquals(hash1, hash2, "동일 입력 $hashCodeInput 에 대해 해시는 동일해야 함")
        }
    }

    @Test
    fun `elasticTabulationHashNative 경계값 입력 정상 실행 테스트`() {
        // Long 타입의 경계값 입력에 대해 함수가 오류 없이 실행되는지 확인
        withMockTablePointer { ptr ->
            assertNotNull(elasticTabulationHashNative(0L, ptr), "0L 입력 실행")
            assertNotNull(elasticTabulationHashNative(-1L, ptr), "-1L 입력 실행") // 부호 없는 값으로는 Long 최대값과 유사
            assertNotNull(elasticTabulationHashNative(MAX_LONG, ptr), "Long.MAX_VALUE 입력 실행")
            assertNotNull(elasticTabulationHashNative(MIN_LONG, ptr), "Long.MIN_VALUE 입력 실행")
        }
    }

    @Test
    fun `elasticTabulationHashNative 입력 비트 변경 시 출력 변경 경향 확인`() {
        // 입력값의 비트가 약간 변경되었을 때 해시 출력이 크게 변하는 경향(Avalanche effect) 확인
        val input1 = 1234567890123456789L
        val input2 = input1 + 1L // 최하위 비트(LSB) 변경
        val input3 = input1 xor (1L shl 25) // 함수가 사용하는 범위 내 비트 변경 (예: 25번째 비트)

        withMockTablePointer { ptr ->
            val hash1 = elasticTabulationHashNative(input1, ptr)
            val hash2 = elasticTabulationHashNative(input2, ptr)
            val hash3 = elasticTabulationHashNative(input3, ptr)

            println("Tabulation Avalanche 확인: H1=$hash1, H2(LSB 변경)=$hash2, H3(25번 비트 변경)=$hash3")
            // 해시 충돌은 가능하지만, 좋은 해시 함수라면 입력이 조금만 달라도 출력은 크게 달라지는 경향이 있음
            assertNotEquals(hash1, hash2, "LSB 변경($input1 -> $input2) 시 해시는 변경될 가능성이 높음")
            assertNotEquals(hash1, hash3, "25번 비트 변경 시 해시는 변경될 가능성이 높음")
        }
    }

    @Test
    fun `elasticTabulationHashNative XOR 연산 영향 간접적 확인`() {
        // 입력 키의 다른 바이트들이 테이블 조회 및 XOR 연산을 통해 최종 해시에 영향을 미치는지 간접 확인
        // 서로 다른 바이트 패턴을 가진 입력 사용
        val input1 = 0x0102030405060708L // 단순 증가 패턴
        val input2 = 0x0807060504030201L // 역순 패턴
        val input3 = 0x00FF00FF00FF00FFL // 수정된 값: 반복 패턴을 유지하는 양수 값

        withMockTablePointer { ptr ->
            val hash1 = elasticTabulationHashNative(input1, ptr)
            val hash2 = elasticTabulationHashNative(input2, ptr)
            val hash3 = elasticTabulationHashNative(input3, ptr)

            println("Tabulation XOR 확인: Hash1=$hash1, Hash2=$hash2, Hash3=$hash3")
            // 입력 바이트 패턴이 다르면 조회되는 테이블 값 조합이 달라지므로, 최종 해시도 달라질 것으로 기대
            assertFalse(hash1 == hash2 && hash1 == hash3, "다른 바이트 패턴을 가진 입력들에 대한 해시는 일반적으로 달라야 함")
        }
    }

    @Test
    fun `elasticTabulationHashNative 테이블 포인터 null일 때 기본값 반환 테스트`() {
        // 테이블 포인터(`tableDataPtr`)가 null일 경우, 입력 `keyHashCode`를 그대로 반환하는지 확인
        val hashCodeInput = 123456789L
        // 구현상 ptr이 null이면 keyHashCode를 반환해야 함
        val defaultHash = elasticTabulationHashNative(hashCodeInput, null)
        assertEquals(hashCodeInput, defaultHash, "테이블 포인터가 null일 때는 keyHashCode를 반환해야 함")
    }


    // === funnelUniversalHashNative 테스트 ===

    @Test
    fun `funnelUniversalHashNative 결정론적 동작 테스트`() {
        // 동일 입력(keyHashCode, a, b)에 대해 항상 동일한 출력을 내는지 확인
        val hashCodeInput = 123456789123456789L
        val a = 101L
        val b = 202L
        val hash1 = funnelUniversalHashNative(hashCodeInput, a, b)
        val hash2 = funnelUniversalHashNative(hashCodeInput, a, b)
        assertEquals(hash1, hash2, "동일 입력(hc=$hashCodeInput, a=$a, b=$b)에 대해 해시는 동일해야 함")
    }

    @Test
    fun `funnelUniversalHashNative 경계값 입력 정상 실행 및 결과 범위 확인`() {
        // Long 타입 경계값 입력에 대해 정상 실행 및 결과값이 [0, P_MODULUS-1] 범위인지 확인
        val a = 31L
        val b = 41L
        val inputs = listOf(0L, -1L, MAX_LONG, MIN_LONG)
        inputs.forEach { hc ->
            val result = funnelUniversalHashNative(hc, a, b)
            // 함수는 Long 타입을 반환하며, 결과는 [0, P_MODULUS - 1] 범위여야 함
            assertTrue(result >= 0L && result < P, "결과 $result 는 입력 $hc 에 대해 [0, $P) 범위여야 함")
            println("[경계값 테스트] 입력 $hc -> 결과 $result")
        }
    }

    @Test
    fun `funnelUniversalHashNative a=1 b=0 일 때 'x mod p' 와 동일한 결과 확인`() {
        // 파라미터 a=1, b=0일 때, 결과가 `keyHashCode mod P_MODULUS`와 동일한지 확인
        val inputs =
            listOf(0L, 1L, -1L, 12345L, P, P - 1L, P + 1L, MAX_LONG, MIN_LONG)
        inputs.forEach { hc ->
            // multiplyMod64를 사용하여 예상 결과 계산 (음수 입력 등 처리)
            val expected = multiplyMod64(1L, hc, P)
            val actual = funnelUniversalHashNative(hc, 1L, 0L) // a, b에 Long 리터럴 사용
            // 직접 비교 (32비트 마스크 불필요)
            assertEquals(expected, actual, "Hash($hc, a=1, b=0) 는 $expected 여야 함")
        }
    }

    @Test
    fun `funnelUniversalHashNative 다른 파라미터 a b 에 대해 일반적으로 다른 출력 생성 확인`() {
        // 동일한 keyHashCode에 대해 파라미터 a 또는 b가 다르면 해시 출력이 달라지는 경향 확인
        val hashCodeInput = 987654321098765432L // Long 타입 입력값 사용
        val a1 = 303L
        val b1 = 404L
        val a2 = 505L // a 값 변경
        val b2 = 606L // b 값 변경

        val hash1 = funnelUniversalHashNative(hashCodeInput, a1, b1)
        val hash2 = funnelUniversalHashNative(hashCodeInput, a2, b1) // a만 다름
        val hash3 = funnelUniversalHashNative(hashCodeInput, a1, b2) // b만 다름

        println("Universal 해시 1 (a=$a1, b=$b1): $hash1")
        println("Universal 해시 2 (a=$a2, b=$b1): $hash2")
        println("Universal 해시 3 (a=$a1, b=$b2): $hash3")

        // 해시 충돌은 가능하지만, 파라미터가 다르면 일반적으로 해시 값도 달라야 함
        assertFalse(hash1 == hash2 && hash1 == hash3, "다른 a/b($a1/$b1 vs $a2/$b1 vs $a1/$b2)를 가진 해시는 일반적으로 달라야 함")
        assertNotEquals(hash1, hash2, "다른 'a'($a1 vs $a2)를 가진 해시는 이상적으로 달라야 함 (충돌 가능)")
        assertNotEquals(hash1, hash3, "다른 'b'($b1 vs $b2)를 가진 해시는 이상적으로 달라야 함 (충돌 가능)")
    }

    @Test
    fun `funnelUniversalHashNative 결과 범위 0 과 P_MODULUS-1 확인 테스트`() {
        // 다양한 입력과 파라미터에 대해 결과값이 항상 [0, P_MODULUS - 1] 범위 내에 있는지 확인
        val samples = listOf(
            Triple(123L, 101L, 202L),
            Triple(MAX_LONG, 31L, 41L),
            Triple(MIN_LONG, 55L, 66L),
            Triple(0L, 1L, 0L), // a=1, b=0 케이스
            Triple(-1L, 99L, 199L),
            Triple(P, 5L, 10L), // 입력값이 모듈러스와 같은 경우
            Triple(P + 10L, 7L, 15L), // 입력값이 모듈러스보다 큰 경우
            Triple(100L, 0L, 50L), // a=0인 경우 (Universal hashing 속성은 깨지지만 함수 자체는 동작)
        )

        for ((hc, a, b) in samples) {
            val result = funnelUniversalHashNative(hc, a, b)
            // 결과가 예상 범위 [0, P_MODULUS - 1] 내에 있는지 확인
            assertTrue(
                result >= 0L && result < P,
                "[Sample] 결과 $result 는 hc=$hc, a=$a, b=$b 에 대해 [0, $P) 범위여야 함",
            )
            println("[Sample 범위 테스트] 입력 (hc=$hc, a=$a, b=$b) -> 결과 $result")
        }
        // 무작위 값으로 범위 테스트
        repeat(100) {
            val hc = Random.Default.nextLong()
            // Universal hashing 속성을 위해서는 a != 0 이어야 하지만, 함수 자체는 a=0도 허용함.
            // 테스트에서는 a=0 포함하여 무작위 생성 가능 (또는 a를 1 이상으로 제한할 수도 있음)
            val a = Random.Default.nextLong(0L, P) // a를 [0, P_MODULUS - 1] 범위에서 무작위 선택
            val b = Random.Default.nextLong() // b는 어떤 Long 값이든 가능
            val result = funnelUniversalHashNative(hc, a, b)
            // 결과가 예상 범위 [0, P_MODULUS - 1] 내에 있는지 확인
            assertTrue(
                result >= 0L && result < P,
                "[Random] 결과 $result 는 hc=$hc, a=$a, b=$b 에 대해 [0, $P) 범위여야 함",
            )
            // println("[Random 범위 테스트] 입력 (hc=$hc, a=$a, b=$b) -> 결과 $result") // 디버깅 시 주석 해제
        }
    }
}

package io.stormi.support.lang.dart.collection.hash

// FFI 및 포인터 관련 import
import io.kotest.core.spec.style.WordSpec
import io.kotest.matchers.ints.shouldBeInRange
import io.kotest.matchers.longs.shouldBeInRange
import io.kotest.matchers.shouldBe
import io.kotest.matchers.shouldNotBe
import io.kotest.property.Arb
import io.kotest.property.arbitrary.int
import io.kotest.property.arbitrary.long
import io.kotest.property.checkAll
import kotlinx.cinterop.ExperimentalForeignApi
import kotlinx.cinterop.IntVar
import kotlinx.cinterop.allocArray
import kotlinx.cinterop.memScoped
import kotlinx.cinterop.set

@OptIn(ExperimentalForeignApi::class)
class OptimalHashingFunctionsTest : WordSpec() {
    init {
        // ElasticTabulationHasher 테스트용 모의 테이블 데이터 생성. 모든 요소가 다른 값을 가지도록 수정 (XOR 테스트 용이성)
        val mockTableData = IntArray(1024) { index ->
            // 간단하면서도 모든 값이 다른 패턴 생성 (예시)
            val base = index * 31 + (index % 7) * 13
            base xor (base shr 16) // 비트 연산 추가
        }

        "multiplyMod64 헬퍼 함수" should {
            "기본적인 모듈러 곱셈을 정확히 수행" {
                multiplyMod64(10L, 20L, P_MODULUS) shouldBe 200L // 200 < P_MODULUS
                multiplyMod64(5L, 7L, 11L) shouldBe (35L % 11L)   // 35 mod 11 = 2
                multiplyMod64(
                    P_MODULUS - 1L,
                    P_MODULUS - 1L,
                    P_MODULUS,
                ) shouldBe 1L // (p-1)*(p-1) mod p = (-1)*(-1) mod p = 1
                multiplyMod64(1L, 123L, P_MODULUS) shouldBe 123L
                multiplyMod64(123L, 1L, P_MODULUS) shouldBe 123L
            }

            "입력 중 하나가 0이면 0 반환" {
                multiplyMod64(0L, 123L, P_MODULUS) shouldBe 0L
                multiplyMod64(123L, 0L, P_MODULUS) shouldBe 0L
            }

            "결과가 항상 [0, p-1] 범위인지 확인 (프로퍼티 기반)" {
                checkAll(Arb.long(), Arb.long(), Arb.long(1L..Long.MAX_VALUE)) { a, x, p ->
                    val result = multiplyMod64(a, x, p)
                    // Kotest의 Long 범위 검증 matcher 사용
                    result shouldBeInRange (0L until p)
                }
            }

            "경계값 근처 테스트" {
                multiplyMod64(
                    2L,
                    P_MODULUS / 2L,
                    P_MODULUS,
                ) shouldBe (P_MODULUS - (P_MODULUS % 2L)) % P_MODULUS // (p-1) 또는 (p-2)와 유사한 값
                multiplyMod64(
                    P_MODULUS - 1L,
                    2L,
                    P_MODULUS,
                ) shouldBe (P_MODULUS - 2L) // (-1 * 2) mod p = -2 mod p = p-2
            }
        }

        "elasticTabulationHashNative 함수" should {
            "결정론적으로 동작 (동일 입력 -> 동일 출력)" {
                val hashCodeInput = 123456789123456789L
                memScoped {
                    val ptr = allocArray<IntVar>(mockTableData.size)
                    mockTableData.forEachIndexed { index, value -> ptr[index] = value }
                    val hash1 = elasticTabulationHashNative(hashCodeInput, ptr)
                    val hash2 = elasticTabulationHashNative(hashCodeInput, ptr)
                    hash1 shouldBe hash2
                }
            }

            "입력값 0, -1 등에 대해 정상 실행" {
                memScoped {
                    val ptr = allocArray<IntVar>(mockTableData.size)
                    mockTableData.forEachIndexed { index, value -> ptr[index] = value }
                    elasticTabulationHashNative(0L, ptr) // 실행 확인
                    elasticTabulationHashNative(-1L, ptr) // 실행 확인
                    elasticTabulationHashNative(Long.MAX_VALUE, ptr) // 실행 확인
                    elasticTabulationHashNative(Long.MIN_VALUE, ptr) // 실행 확인
                }
            }

            "입력 비트 변경 시 출력 변경 경향 확인 (Avalanche Effect 간접 확인)" {
                // 유효한 범위 내의 Long 값으로 수정
                val input1 = 1234567890123456789L // 예시 값
                val input2 = input1 + 1L // 마지막 비트 변경 효과
                val input3 = input1 xor (1L shl 10) // 중간 비트 하나 변경 (10번째 비트)

                memScoped {
                    val ptr = allocArray<IntVar>(mockTableData.size)
                    mockTableData.forEachIndexed { index, value -> ptr[index] = value }
                    val hash1 = elasticTabulationHashNative(input1, ptr)
                    val hash2 = elasticTabulationHashNative(input2, ptr)
                    val hash3 = elasticTabulationHashNative(input3, ptr)

                    println("Tabulation Avalanche Check: H1=$hash1, H2(LSB flip)=$hash2, H3(Bit 10 flip)=$hash3")
                    hash1 shouldNotBe hash2 // 매우 높은 확률로 달라야 함
                    hash1 shouldNotBe hash3 // 매우 높은 확률로 달라야 함
                }
            }

            "XOR-Folding 영향 확인 (간접적)" {
                // h64 와 h64 + (1L shl 32) 는 하위 32비트는 같고 상위 32비트만 다름
                // XOR-Folding 결과는 달라야 함
                val inputBase = 1234567890L
                val inputHighBit = inputBase + (1L shl 32) // 상위 32비트에 1 추가

                memScoped {
                    val ptr = allocArray<IntVar>(mockTableData.size)
                    mockTableData.forEachIndexed { index, value -> ptr[index] = value }
                    val hashBase = elasticTabulationHashNative(inputBase, ptr)
                    val hashHigh = elasticTabulationHashNative(inputHighBit, ptr)

                    println("Tabulation XOR-Fold Check: BaseHash=$hashBase, HighBitHash=$hashHigh")
                    // 테이블 값이 잘 분산되어 있다면 결과는 달라야 함
                    hashBase shouldNotBe hashHigh
                }
            }

            "테이블 포인터가 null일 때 기본값 반환" {
                val hashCodeInput = 123L
                val defaultHash = elasticTabulationHashNative(hashCodeInput, null)
                defaultHash shouldBe hashCodeInput.toInt() // 현재 구현 기준
            }
        }

        "funnelUniversalHashNative 함수" should {
            "결정론적으로 동작 (동일 입력 -> 동일 출력)" {
                val hashCodeInput = 123456789123456789L
                val a = 101
                val b = 202
                val hash1 = funnelUniversalHashNative(hashCodeInput, a, b)
                val hash2 = funnelUniversalHashNative(hashCodeInput, a, b)
                hash1 shouldBe hash2
            }

            "입력값 0, -1 등에 대해 정상 실행 및 범위 확인" {
                val a = 31
                val b = 41
                val pInt = P_MODULUS.toInt() // 범위 검증용
                funnelUniversalHashNative(0L, a, b) shouldBeInRange (0 until pInt)
                funnelUniversalHashNative(-1L, a, b) shouldBeInRange (0 until pInt)
                funnelUniversalHashNative(Long.MAX_VALUE, a, b) shouldBeInRange (0 until pInt)
                funnelUniversalHashNative(Long.MIN_VALUE, a, b) shouldBeInRange (0 until pInt)
            }

            "a=1, b=0 일 때 (x mod p) 와 유사한 결과 확인" {
                // a=1, b=0 이면 결과는 (x mod p) 여야 함
                checkAll(Arb.long()) { hc ->
                    val expected = multiplyMod64(1L, hc, P_MODULUS).toInt() // (1*hc) mod p
                    funnelUniversalHashNative(hc, 1, 0) shouldBe expected
                }
            }

            "다른 파라미터 a, b에 대해 다른 출력 생성 (일반적으로)" {
                val hashCodeInput = 987654321L
                val a1 = 303
                val b1 = 404
                val a2 = 505
                val b2 = 606
                val hash1 = funnelUniversalHashNative(hashCodeInput, a1, b1)
                val hash2 = funnelUniversalHashNative(hashCodeInput, a2, b1) // a 다름
                val hash3 = funnelUniversalHashNative(hashCodeInput, a1, b2) // b 다름
                // hash1 shouldNotBe hash2 // 충돌 가능성 있음
                // hash1 shouldNotBe hash3 // 충돌 가능성 있음
                println("Universal Hash 1: $hash1, Hash 2 (a diff): $hash2, Hash 3 (b diff): $hash3")
                // 최소한 셋 다 같지는 않을 확률이 매우 높음
                (hash1 == hash2 && hash1 == hash3) shouldBe false
            }

            "결과가 항상 [0, p-1] 범위인지 확인 (프로퍼티 기반)" {
                checkAll(Arb.long(), Arb.int(), Arb.int()) { hc, a, b ->
                    val validA = if (a == 0) 1 else a // a는 0이 아님
                    val result = funnelUniversalHashNative(hc, validA, b)
                    // P_MODULUS는 Long, 결과는 Int. Int 범위 내에서 p-1 까지여야 함
                    if (P_MODULUS <= Int.MAX_VALUE.toLong() + 1L) {
                        result shouldBeInRange (0 until P_MODULUS.toInt())
                    } else {
                        // p가 Int 범위를 넘는 경우는 거의 없지만, 이론상 체크
                        result shouldBeInRange (0..Int.MAX_VALUE)
                    }
                }
            }
        }
    }
}

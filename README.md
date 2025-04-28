# Platform Optimal Hash
**Note: This project is an experimental implementation and should be used with caution.**

논문 "[Optimal Bounds for Open Addressing Without Reordering](https://arxiv.org/abs/2501.02305)" 의 해싱 기법을 AI 분석을 통해
네이티브 함수 구현.

- 해시 테이블 및 기타 데이터 구조에서 균일한 해싱
  - Tabulation Hashing
  - Universal Hashing
- 지원 플랫폼:
  - Android
  - iOS
  - Linux
  - macOS
  - Windows

### Tabulation Hashing

Tabulation Hashing 함수 사용:

```kotlin
fun main() {
  val tableSize = 1024 // 4개의 테이블 * 각 256개 항목
  memScoped {
    val table = allocArray<LongVar>(tableSize)
    // 테이블을 랜덤 값으로 초기화
    for (i in 0 until tableSize) {
      table[i] = (0..Long.MAX_VALUE).random()
    }
    val key = 12345L
    val hash = elasticTabulationHashNative(key, table)
    println("Tabulation Hash: $hash")
  }
}
```

### Universal Hashing

Universal Hashing 함수 사용(`a`와 `b` 파라미터를 랜덤으로 선택):

```kotlin
fun main() {
  val p = 4294967311L // P_MODULUS
  val a = (1 until p).random()
  val b = (0 until p).random()
  val key = 12345L
  val hash = funnelUniversalHashNative(key, a, b)
  println("Universal Hash: $hash")
}
```

## API

### `elasticTabulationHashNative(keyHashCode: Long, tableDataPtr: COpaquePointer?): Long`

주어진 키의 Tabulation Hash를 계산합니다.

- **파라미터**:
  - `keyHashCode`: 해싱할 키 (64비트 Long).
  - `tableDataPtr`: 랜덤 Long 값으로 구성된 사전 계산 테이블의 포인터.
- **반환값**: 계산된 해시 값 (Long).

### `funnelUniversalHashNative(keyHashCode: Long, a: Long, b: Long): Long`

주어진 키의 Universal Hash를 계산합니다.

- **파라미터**:
  - `keyHashCode`: 해싱할 키 (64비트 Long).
  - `a`: 곱셈 계수 (1부터 p-1 사이의 랜덤 Long).
  - `b`: 덧셈 계수 (0부터 p-1 사이의 랜덤 Long).
- **반환값**: 계산된 해시 값 (0부터 p-1 사이의 Long).

### 요구 사항

- Kotlin: 2.1.20
- Gradle: 8.9.1
- Java: 17

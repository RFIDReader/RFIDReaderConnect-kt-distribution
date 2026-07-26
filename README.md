# RFIDReaderConnect for Android

RFIDReaderConnect is the supported Kotlin SDK for discovering, connecting to,
configuring, and reading tags from RFIDReader hardware on Android phones,
tablets, and embedded devices. This distribution repository hosts a full Maven
repository (AAR + POM + Gradle module metadata + Javadoc JAR), the compiled AAR
and Javadoc archive for manual download, and the hosted API documentation.

> Latest release: **0.0.2** · Minimum deployment: **Android 8.0 (API 26)**

## Start here

| Resource | Link |
| --- | --- |
| API reference | [Browse RFIDReaderConnect documentation](docs/index.html) |
| Maven repository | [`maven/`](maven) — `com.aerouhf:helios-sdk:<version>` |
| Binary AAR | [HeliosSDK.aar](releases/download/v0.0.2/HeliosSDK.aar) |
| Javadoc archive | [HeliosSDK-javadoc.jar](releases/download/v0.0.2/HeliosSDK-javadoc.jar) |
| Source repository | `https://github.com/RFIDReader/HeliosSDK-android` |

No sources JAR is published: this is a proprietary SDK whose AAR ships
R8-obfuscated. The AAR, its POM/module metadata, the Javadoc JAR, and the
generated documentation are the published artifacts.

## Install with Gradle and Maven (recommended)

Each release publishes a full Maven layout under [`maven/`](maven), served
directly from raw GitHub. Because a real POM is published, Gradle resolves the
SDK's transitive dependencies automatically.

Add the raw-GitHub Maven repository to `dependencyResolutionManagement` in the
project's `settings.gradle.kts`:

```kotlin
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
        maven("https://raw.githubusercontent.com/RFIDReader/HeliosSDK-android-distribution/master/maven")
        maven("https://jitpack.io") // optional fallback
    }
}
```

Add the SDK to the application module's `build.gradle.kts`:

```kotlin
dependencies {
    implementation("com.aerouhf:helios-sdk:<version>")
}
```

Replace `<version>` with a published version such as `0.0.2`. Pin an explicit
version in production so builds remain reproducible.

## Install with Gradle and JitPack

As a fallback, JitPack builds the SDK straight from the source repository. The
JitPack coordinate stays repo-based because the GitHub repository name is
unchanged:

```kotlin
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
        maven("https://jitpack.io")
    }
}
```

```kotlin
dependencies {
    implementation("com.github.RFIDReader:HeliosSDK-android:v0.0.2")
}
```

Pin an explicit release tag in production so builds remain reproducible.

## Install the AAR manually

1. Download [HeliosSDK.aar](releases/download/v0.0.2/HeliosSDK.aar).
2. Place it in the application module's `libs` directory, for example
   `app/libs/HeliosSDK.aar`.
3. Add the AAR and its runtime dependencies to `app/build.gradle.kts`:

```kotlin
dependencies {
    implementation(files("libs/HeliosSDK.aar"))

    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.webkit:webkit:1.12.1")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-core:1.9.0")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.9.0")
    implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.7.3")
}
```

A standalone AAR does not include a Maven POM, so its transitive dependencies
must be declared by the application. Gradle/JitPack consumers receive them
automatically.

## Recommended application architecture

Keep platform discovery, SDK ownership, delegate handling, and UI state
separate:

- A scanner owns Android BLE discovery and exposes discovered devices.
- An app-scoped `ViewModel` owns the active `RFIDReader` for its full lifecycle.
- One `RFIDReaderDelegate` translates SDK callbacks into observable app state.
- Activities and Composables send commands through that state layer and render
  callback-driven state. They do not parse reader messages directly.
- Transport-specific permission handling stays at the application boundary.

This is the same pattern used by the reference application.

### 1. Create app-scoped reader state and a delegate

```kotlin
import android.app.Application
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.AndroidViewModel
import com.aerouhf.helios_sdk.RFIDReader
import com.aerouhf.helios_sdk.RFIDReaderDelegate
import com.aerouhf.helios_sdk.RFIDTag

class ReaderState(application: Application) : AndroidViewModel(application) {
    var reader by mutableStateOf<RFIDReader?>(null)
    var isConnected by mutableStateOf(false)
        private set
    var isScanning by mutableStateOf(false)
        private set
    val tags = mutableStateListOf<RFIDTag>()
    var lastError by mutableStateOf<Throwable?>(null)
        private set

    val delegate = object : RFIDReaderDelegate {
        override fun rfidReaderDidConnect() {
            isConnected = true
        }

        override fun rfidReaderDidBecomeReady() {
            isConnected = true
        }

        override fun rfidReaderDidDisconnect() {
            isConnected = false
            isScanning = false
        }

        override fun rfidReaderDidStartScanning() {
            isScanning = true
        }

        override fun rfidReaderDidStopScanning() {
            isScanning = false
        }

        override fun rfidReaderDidReadTag(tag: RFIDTag) {
            tags += tag
        }

        override fun rfidReaderDidReceiveMessage(message: Any) {
            // Route typed configuration responses to the relevant app state.
        }

        override fun rfidReaderDidEncounteredError(error: Throwable) {
            lastError = error
        }
    }

    fun disconnect() {
        reader?.disconnect()
        reader = null
    }

    override fun onCleared() {
        reader?.disconnect()
    }
}
```

SDK delegate callbacks are delivered on the Android main thread, so Compose
state and other UI-owned state can be updated directly. Obtain the `ViewModel`
at the activity or navigation-graph boundary rather than creating it in a
transient screen:

```kotlin
class MainActivity : ComponentActivity() {
    private val readerState: ReaderState by viewModels()
}
```

### 2. Request BLE permissions and discover readers

The SDK manifest declares the required Bluetooth permissions, but the host
application must request runtime permissions before scanning or connecting.

```kotlin
val blePermissions =
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
        arrayOf(
            Manifest.permission.BLUETOOTH_SCAN,
            Manifest.permission.BLUETOOTH_CONNECT,
        )
    } else {
        arrayOf(Manifest.permission.ACCESS_FINE_LOCATION)
    }

val permissionLauncher =
    rememberLauncherForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions(),
    ) { result ->
        if (result.values.all { it }) {
            bleScanner.startScanning()
        }
    }

LaunchedEffect(Unit) {
    permissionLauncher.launch(blePermissions)
}

DisposableEffect(Unit) {
    onDispose { bleScanner.stopScanning() }
}
```

Use `BluetoothLeScanner` for discovery, de-duplicate results by device MAC
address, and retain the scanner while its screen is active. Stop discovery
before connecting to the selected reader.

### 3. Connect over BLE

```kotlin
import android.bluetooth.BluetoothDevice
import com.aerouhf.helios_sdk.RFIDReader
import com.aerouhf.helios_sdk.RFIDReaderModel
import com.aerouhf.helios_sdk.transport.TransportType

fun connectBle(device: BluetoothDevice) {
    bleScanner.stopScanning()
    readerState.reader?.disconnect()

    readerState.reader = RFIDReader(
        model = RFIDReaderModel.MARK3_HH7,
        name = device.name,
        transport = TransportType.Ble(
            context = applicationContext,
            identifier = device.address,
            connectionTimeout = 30_000L,
            maxRetries = 1,
            retryInterval = 5,
        ),
        delegate = readerState.delegate,
    ).also { it.connect() }
}
```

Retain both the reader and its delegate for the complete connection lifecycle.
Wait for `rfidReaderDidBecomeReady()` before sending configuration or inventory
commands.

### 4. Start and stop inventory

Commands are asynchronous. Results and state changes arrive through
`RFIDReaderDelegate`:

```kotlin
import com.aerouhf.helios_sdk.RFIDReaderTagMetadata

readerState.reader?.startAsyncInventory(
    metadata = listOf(
        RFIDReaderTagMetadata.RETURN_RSSI,
        RFIDReaderTagMetadata.RETURN_TIMESTAMP,
        RFIDReaderTagMetadata.RETURN_READ_COUNT,
    ),
)

readerState.reader?.stopAsyncInventory()
```

Use `rfidReaderDidReadTag`, `rfidReaderDidStartScanning`, and
`rfidReaderDidStopScanning` as the authoritative notification stream instead
of assuming that a button tap completed the command.

## Wi-Fi connection

For a reader reachable by hostname or IP address:

```kotlin
import com.aerouhf.helios_sdk.RFIDReader
import com.aerouhf.helios_sdk.RFIDReaderModel
import com.aerouhf.helios_sdk.transport.TransportType
import com.aerouhf.helios_sdk.transport.WiFiTransportMode

readerState.reader = RFIDReader(
    model = RFIDReaderModel.MARK3_HH7,
    name = "Warehouse Reader",
    transport = TransportType.WiFi(
        host = "rfidreader.local",
        httpPort = "80",
        tcpPort = "81",
        udpPort = "82",
        mode = WiFiTransportMode.TCP,
    ),
    delegate = readerState.delegate,
).also { it.connect() }
```

TCP is the recommended default for reliable command/response traffic. The
reader and Android device must be reachable on the same network when using a
local address.

## USB connection

Android USB Host mode requires the host application to enumerate devices and
obtain permission with `UsbManager.requestPermission()` before constructing the
reader:

```kotlin
readerState.reader = RFIDReader(
    model = RFIDReaderModel.MARK3_HH7,
    name = usbDevice.productName ?: "RFID Reader",
    transport = TransportType.Usb(
        context = applicationContext,
        device = usbDevice,
    ),
    delegate = readerState.delegate,
).also { it.connect() }
```

The reference application filters for the supported Espressif USB vendor ID
`0x303A` before presenting devices to the user.

## Platform permissions

The AAR contributes these declarations through manifest merging:

```xml
<!-- Android 12+ -->
<uses-permission
    android:name="android.permission.BLUETOOTH_SCAN"
    android:usesPermissionFlags="neverForLocation" />
<uses-permission android:name="android.permission.BLUETOOTH_CONNECT" />

<!-- Android 11 and earlier -->
<uses-permission
    android:name="android.permission.ACCESS_FINE_LOCATION"
    android:maxSdkVersion="30" />

<!-- Wi-Fi transport and OTA -->
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />

<!-- Optional transports -->
<uses-feature android:name="android.hardware.bluetooth_le" android:required="false" />
<uses-feature android:name="android.hardware.usb.host" android:required="false" />
```

`BLUETOOTH_SCAN` and `BLUETOOTH_CONNECT` are runtime permissions on Android 12
and newer. `ACCESS_FINE_LOCATION` is required for BLE discovery on supported
older Android versions. USB device access uses a separate per-device permission
flow managed by `UsbManager`.

## Firmware updates

Wi-Fi readers can request an HTTPS-pull update:

```kotlin
readerState.reader?.performOTA(version = "1.2.3")
```

BLE and USB readers can stream a downloaded firmware image directly. Keep the
returned client if the UI supports best-effort cancellation:

```kotlin
val ota = readerState.reader?.performStreamingOTA(
    imageData = firmwareBytes,
    version = "1.2.3",
    delegate = streamingOTADelegate,
)

ota?.abort()
```

Streaming OTA progress and completion are reported through
`StreamingOTAClientDelegate` on the Android main thread.

## Connection lifecycle guidelines

- Construct one `RFIDReader` for the selected transport and retain it.
- Wait for `rfidReaderDidBecomeReady()` before sending reader commands.
- Request runtime permissions before BLE discovery or connection.
- Stop BLE discovery before connecting.
- Request USB permission before creating a USB reader.
- Call `disconnect()` when replacing a reader or ending the session.
- Treat delegate callbacks, rather than UI actions, as the source of truth for
  connection and inventory state.

## Troubleshooting

### BLE discovery returns no devices

Confirm Bluetooth is enabled and the correct runtime permissions were granted.
On Android 12 and newer both `BLUETOOTH_SCAN` and `BLUETOOTH_CONNECT` are
required. On older supported releases, grant location permission and ensure
device location services are enabled where the platform requires them.

### The reader connects but commands fail immediately

Wait for `rfidReaderDidBecomeReady()`. A transport connection can be established
before reader initialization has completed.

### The manual AAR builds with missing-class errors

Declare all runtime dependencies shown in **Install the AAR manually**. A bare
AAR does not carry dependency metadata.

### USB connection fails

Verify that the Android device supports USB Host mode, the reader appears in
`UsbManager.deviceList`, and the app received permission for that exact
`UsbDevice` before calling `connect()`.

## Documentation and support

The generated symbol reference is available under [docs](docs/index.html).
When reporting an integration issue, include the Android version, device model,
reader model, transport, firmware version, SDK release, and the delegate error
description.

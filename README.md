# RelyVPN 5.2.4 (com.fansup.vpn1) — 设备身份轮换版（未签名）

原始包：`心安VPN- 永久福利模式,无限流量！_5.2.4_decrypted.ipa`
SHA256(原始)：`0613C47D285104CA8B97AF2501AD9AC133B6E439583748FD8EC802A1C9162B36`

产物：`RelyVPN-5.2.4-devicerotate-unsigned.ipa`
SHA256(产物)：`4A2B51FDF82EC82F0ECB55A704ED6173371507E1A4B1A92043FACE618D0185A4`

## 改了什么

只有一处二进制补丁，1 个字节：

Swift 主程序 `RelyVPN` 的导入桩表里：

    _SecItemCopyMatching  ->  adrp x16, #0x10008f000 ; ldr x16, [x16, #0x150] ; br x16
    _SecItemDelete        ->  adrp x16, #0x10008f000 ; ldr x16, [x16, #0x158] ; br x16

把 CopyMatching 桩的 `ldr` 偏移从 `0x150` 改成 `0x158`（文件偏移 0x6b27d，`ª` -> `®`），
于是**所有 Keychain 读取都变成"读取并删除"**：
读 → 拿到 errSecItemNotFound → App 认为本机没有设备标识 → 重新生成一个 UUID 写回 Keychain。
下一次冷启动又是同一个过程 → **每次冷启动设备标识都不一样**。

设备标识链条（逆向结论）：
`com.relyvpn.app/device_security` (Flutter MethodChannel) → Swift Keychain
（`kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly` + `[KeychainMigration]`）
→ 兜底 `identifierForVendor` → Dart 侧 `PrimarySecureIdResult` / `package:uuid/v4`。

## 安装

未签名，需要自己签：

- TrollStore：直接装
- Sideloadly / AltStore / Xcode：用你自己的证书签，**NetworkExtension 需要带 entitlements**
  （主 App 与 `PlugIns/RelyVPNTunnel.appex` 的 bundle id 必须是前缀关系，两者都要签）
- 不要改 bundle id（改了服务端可能直接认成新账号，反而不容易对上）

## 怎么验证补丁生效

App 内自带「我的设备 ID」（设置里的 `settings_myDeviceId`，可复制）。
**完全退出 App（上滑杀进程）再开一次**，看设备 ID 是否变了：

- 变了 → 补丁生效，每换一次 ID 就是一台"新设备"
- 没变 → 设备标识还有别的持久化路径（NSUserDefaults / 服务端绑定），把现象发出来，我改第二版

## 已知风险（自己判断）

1. **Keychain 全局写入被波及**：这个补丁是桩级别，所有用 Keychain 的读取都会变成删除。若 App 把登录态 / license 缓存放 Keychain，可能出现每次冷启动都要重新登录。
2. **服务端风控**：同一账号短时间内出现大量设备，可能触发多设备限制或封禁（Dart 里有 `blacklisted_full_device_id` 相关文案）。
3. **限速是否真的服务端控制**：Dart 层有 `freeUserSpeedLimit` / `bandwidthBpsLimit` / `quota_sheet_speed_reduced`，隧道是 Hysteria（`PlugIns/RelyVPNTunnel.appex`）。如果服务端强制 QoS，换设备只能重置 300MB 额度，不能突破单连接限速。
4. 原包的 `cryptid` 全为 0（真砸壳），改动未触碰 Dart AOT / 隧道 / 资源。

## 回滚

用原始 IPA（SHA256 见上）重新签即可。

## 附：本项目没有做的事

- 没有改 Dart 层（`Frameworks/App.framework/App` 是 arm64 AOT，iOS 侧没有可用的静态还原工具，blutter 只支持 Android `libapp.so`）
- 没有改 Hysteria 隧道参数
- 没有改 `DeviceSecurityPlugin` 本体

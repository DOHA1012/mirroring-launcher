# 미러링 바로연결 (Universal Android Mirroring Launcher)

[한글 (Korean)](#한글-사용-설명서) | [English](#english-user-guide)

---

## 한글 사용 설명서

이 패키지는 스마트폰의 **어떤 안드로이드 앱이든** PC 화면에 무선 미러링 창으로 원클릭 기동하고, 키보드와 마우스로 제어할 수 있게 돕는 범용 런처입니다.

## 📥 최신 버전 다운로드 (v1.0.0)
아래 링크에서 런처 패키지 zip 파일을 무료로 다운로드하실 수 있습니다. 다운로드 후 압축을 풀어 사용하세요:
👉 **[미러링 바로연결 Standalone Package 다운로드 (ZIP)](https://github.com/DOHA1012/mirroring-launcher/releases/download/v1.0.0/mirroring_direction.zip)**

### ✨ 주요 핵심 기능
* **비동기 고속 앱 로딩**: 기기 연결 즉시 설치된 모든 앱 목록을 한글/영어 이름으로 즉시 긁어옵니다.
* **즐겨찾기 카드 구성**: 자주 쓰는 앱들을 즐겨찾기에 등록하고 메인 화면에서 카드 클릭 한 번으로 간편하게 시작합니다.
* **실시간 스마트 앱 아이콘 추출**: 앱을 즐겨찾기에 등록하는 순간 폰 내부에서 아이콘(.png)을 즉시 추출하여 PC 화면과 창 아이콘에 고해상도로 반영합니다.
* **동적 창 제목 & 아이콘 스킨**: 실행된 미러링 창의 상단 타이틀과 작업표시줄 아이콘이 **해당 앱 고유의 이름과 아이콘으로 실시간 자동 전환**됩니다.
* **다양한 미러링 모드**: 폰 화면을 끈 채 독립된 가상 창을 쓰는 **독립 가상 창 모드**와, 폰 화면을 그대로 복제하는 **기기 화면 복제 모드** 중 선택할 수 있습니다.
* **설정 자동 저장**: 해상도, IP 주소, 전체화면 유무 및 사용자가 등록한 모든 즐겨찾기 앱 정보와 별칭이 `config.json`에 안전하게 보관됩니다.

---

### 📂 폴더 구성 정보
* 📄 **미러링_바로연결.exe** - 사용자 실행용 GUI 프로그램 (더블 클릭하여 실행)
* 📁 **bin** - 실행에 필요한 핵심 엔진 폴더 (수정하거나 삭제하지 마세요)
  * 📁 `adb` - 안드로이드 연결용 통신 엔진
  * 📁 `scrcpy` - 화면 송출 및 가상 창 생성 엔진

---

### 🚀 사용 및 연결 방법

#### 1단계: 스마트폰 사전 설정 (최초 1회 필수)
1. 스마트폰 **설정** ➡️ **휴대폰 정보** ➡️ **소프트웨어 정보**로 이동합니다.
2. **빌드 번호** 항목을 **7번 연속**으로 연타하여 개발자 옵션을 활성화합니다.
3. 설정 메인 화면으로 돌아와 맨 아래의 **개발자 옵션**으로 들어갑니다.
4. **USB 디버깅** 항목을 찾아서 **활성화(켬)** 상태로 켭니다.

#### 2단계: PC와 무선 연결 자동 설정
1. PC와 스마트폰을 **동일한 와이파이 공유기**에 연결합니다.
2. 스마트폰을 **USB 케이블로 PC에 연결**합니다.
   * *이때 스마트폰 화면에 "USB 디버깅을 허용하시겠습니까?" 팝업이 뜨면 **"이 컴퓨터에서 항상 허용"**에 체크하고 **[허용]**을 누릅니다.*
3. **`미러링_바로연결.exe`**를 실행합니다.
4. 프로그램 창 상단의 **`★ USB 기기로 무선 자동 설정`** 버튼을 누릅니다.
5. "자동 설정이 완료되었습니다" 팝업이 뜨면 **USB 케이블을 분리(해제)**합니다. (이제 무선으로 연결됩니다.)

#### 3단계: 즐겨찾기 앱 등록 및 실행
1. 맨 하단의 **`➕ 전체 앱 스캔 및 즐겨찾기 등록`** 버튼을 누릅니다.
2. 팝업 창에 기기의 앱들이 나열되면 원하는 앱을 검색하거나 더블 클릭하여 이름을 지정하고 즐겨찾기에 등록합니다.
3. 메인 화면에 생성된 해당 앱 카드를 마우스로 클릭하여 선택합니다.
4. 해상도 및 화면 설정에서 원하는 사양을 고른 뒤 **`선택한 앱 실행 및 미러링`** 버튼을 누릅니다.

---

### 🛠️ 문제 해결 (FAQ)

#### Q. 스마트폰을 껐다 켰더니 연결이 안 됩니다.
안드로이드 보안 정책상 폰을 재부팅하면 무선 포트가 닫힙니다. 
* **해결책:** 폰을 다시 USB 케이블로 PC에 연결한 뒤, 실행기를 켜고 **`★ USB 기기로 무선 자동 설정`** 버튼을 다시 한번 눌러주시면 무선 포트가 재개방됩니다.

#### Q. 실행 후 직접 폰 전원 버튼을 눌러 화면을 끄면 PC 화면도 꺼집니다.
* **해결책**: 런처가 스마트폰의 실제 화면(액정)을 자동으로 꺼주기 때문에, 실행 후에는 **전원 버튼을 직접 누르지 마시고 그대로 폰을 냅두시면 됩니다.**

---
---

## English User Guide

This package is a universal launcher designed to wireless-mirror and launch **any Android application** installed on a mobile device onto a high-definition PC window, allowing full keyboard and mouse controls.

## 📥 Download Latest Version (v1.0.0)
You can download the launcher package zip file for free from the link below. Extract and run it:
👉 **[Download Universal Mirroring Launcher Standalone Package (ZIP)](https://github.com/DOHA1012/mirroring-launcher/releases/download/v1.0.0/mirroring_direction.zip)**

### ✨ Core Features
* **Bilingual Async App Loading**: Instantly scans all installed third-party and system activities in both English and Korean.
* **Favorites Card Layout**: Register your frequently used apps and easily launch them with a single click.
* **Real-time Icon Decompression**: The moment you add an app to favorites, its high-res icon (.png) is pulled wirelessly from the phone using a fast unzip pipeline.
* **Dynamic Window Title & Icon Skinning**: When the mirroring window starts, the window title and taskbar icon **dynamically switch to the running app's name and icon**.
* **Flexible Mirroring Modes**: Choose between **Virtual Display Mode** (independent virtual desktop) and **Direct Duplicate Mode** (mirrors phone screen).
* **Auto Save settings**: Resolution, IP address, borderless fullscreen settings, and all registered favorite apps are persisted in `config.json`.

---

### 📂 Folder Structure
* 📄 **미러링_바로연결.exe** - The main GUI launcher program.
* 📁 **bin** - Core engine folder (Do not modify or delete).
  * 📁 `adb` - Android connection engine.
  * 📁 `scrcpy` - Mirroring and virtual window engine.

---

### 🚀 How to Run

#### Step 1: Setup Android Phone (First Time Only)
1. Go to **Settings** ➡️ **About phone** ➡️ **Software information** on your smartphone.
2. Tap **Build number** **7 times** consecutively to enable Developer options.
3. Return to the main Settings menu and tap **Developer options** at the bottom.
4. Locate **USB debugging** and toggle it **ON**.

#### Step 2: Configure Wireless Connection Automatically
1. Connect both your PC and smartphone to the **same Wi-Fi router**.
2. Connect the smartphone to your PC using a **USB cable**.
   * *If the phone prompts "Allow USB debugging?", check **"Always allow from this computer"** and tap **[Allow]**.*
3. Launch **`미러링_바로연결.exe`**.
4. Click the **`★ USB 기기로 무선 자동 설정`** button.
5. Once the setup completes, **disconnect the USB cable**. (The device is now connected wirelessly.)

#### Step 3: Add Favorites & Run
1. Click **`➕ 전체 앱 스캔 및 즐겨찾기 등록`** at the bottom.
2. Double-click any app in the popup list, specify its name, and add it to your favorites.
3. Click the newly created app card in the main grid list.
4. Select your preferred resolution and settings, then click **`선택한 앱 실행 및 미러링`**.

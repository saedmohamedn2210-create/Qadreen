# -*- coding: utf-8 -*-
# globalPlugin.py
# إضافة Qadreen - إدارة ومشاركة روابط البرامج
# يغطي هذا الملف: وضع العرض (Search and Fetch)، وضع التصميم (Design Mode)،
# وصفحة إعدادات لغة الإضافة داخل NVDA Settings.

import os
import json
import time
import tempfile
import threading
import webbrowser
import urllib.parse
import urllib.request

import wx
import api
import ui
import gui
import config
import languageHandler
import addonHandler
import globalPluginHandler
from scriptHandler import script


# مسار ملف البيانات: بجانب هذا الملف مباشرة داخل globalPlugins
ADDON_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(ADDON_DIR, "data.json")


# =====================================================================
# نظام الترجمة الداخلي للإضافة (مستقل عن نظام gettext القياسي في NVDA)
# لأن المستخدم يحتاج التحكم بلغة الإضافة بشكل منفصل عن لغة NVDA نفسها
# =====================================================================

STRINGS = {
	"scriptDescription": {"ar": "فتح نافذة البحث السريع عن روابط البرامج", "en": "Open the quick link search window"},
	"dialogTitleView": {"ar": "قادرين - بحث سريع عن الروابط", "en": "Qadreen - Quick Link Search"},
	"dialogTitleDesign": {"ar": "قادرين - وضع التصميم", "en": "Qadreen - Design Mode"},
	"searchLabel": {"ar": "بحث:", "en": "Search:"},
	"searchCtrlName": {"ar": "مربع البحث السريع", "en": "Quick search box"},
	"groupLabel": {"ar": "المجموعة (Group)", "en": "Group"},
	"groupListName": {"ar": "قائمة المجموعات", "en": "Groups list"},
	"categoryLabel": {"ar": "الفئة (Category)", "en": "Category"},
	"categoryListName": {"ar": "قائمة الفئات", "en": "Categories list"},
	"softwareLabel": {"ar": "البرنامج (Software)", "en": "Software"},
	"softwareListName": {"ar": "قائمة البرامج", "en": "Software list"},
	"copyButton": {"ar": "نسخ الرابط", "en": "Copy link"},
	"addToCopyButton": {"ar": "إضافة إلى النسخ", "en": "Add to copy"},
	"closeButton": {"ar": "إغلاق", "en": "Close"},
	"msgNoSoftwareSelected": {"ar": "لم يتم تحديد برنامج", "en": "No software selected"},
	"msgNoLink": {"ar": "لا يوجد رابط لهذا البرنامج", "en": "This software has no link"},
	"msgCopied": {"ar": "تم النسخ", "en": "Copied"},
	"msgOpeningLink": {"ar": "جاري فتح الرابط", "en": "Opening the link"},
	"msgDesignMode": {"ar": "وضع التصميم", "en": "Design mode"},
	"msgViewMode": {"ar": "وضع العرض", "en": "View mode"},
	"msgSelectGroupFirst": {"ar": "الرجاء اختيار مجموعة أولاً", "en": "Please select a group first"},
	"msgSelectGroupAndCategoryFirst": {"ar": "الرجاء اختيار مجموعة وفئة أولاً", "en": "Please select a group and category first"},
	"msgNameRequired": {"ar": "يجب إدخال اسم", "en": "A name is required"},
	"msgSoftwareNameRequired": {"ar": "يجب إدخال اسم البرنامج", "en": "Software name is required"},
	"msgUrlRequired": {"ar": "يجب إدخال الرابط", "en": "The link is required"},
	"msgNameExists": {"ar": "هذا الاسم موجود مسبقاً", "en": "This name already exists"},
	"msgNameExistsInGroup": {"ar": "هذا الاسم موجود مسبقاً في هذه المجموعة", "en": "This name already exists in this group"},
	"msgNameExistsInCategory": {"ar": "هذا الاسم موجود مسبقاً في هذه الفئة", "en": "This name already exists in this category"},
	"msgAdded": {"ar": "تمت الإضافة", "en": "Added"},
	"msgEdited": {"ar": "تم التعديل", "en": "Edited"},
	"msgDeleted": {"ar": "تم الحذف", "en": "Deleted"},
	"msgSelectItemFirst": {"ar": "حدد عنصراً أولاً", "en": "Select an item first"},
	"msgNoGroupSelected": {"ar": "لم يتم تحديد مجموعة", "en": "No group selected"},
	"msgNoCategorySelected": {"ar": "لم يتم تحديد فئة", "en": "No category selected"},
	"addGroupTitle": {"ar": "إضافة مجموعة", "en": "Add group"},
	"editGroupTitle": {"ar": "تعديل اسم المجموعة", "en": "Edit group name"},
	"groupNameLabel": {"ar": "اسم المجموعة", "en": "Group name"},
	"addCategoryTitle": {"ar": "إضافة فئة", "en": "Add category"},
	"editCategoryTitle": {"ar": "تعديل اسم الفئة", "en": "Edit category name"},
	"categoryNameLabel": {"ar": "اسم الفئة", "en": "Category name"},
	"addSoftwareTitle": {"ar": "إضافة برنامج", "en": "Add software"},
	"editSoftwareTitle": {"ar": "تعديل بيانات البرنامج", "en": "Edit software details"},
	"softwareNameLabel": {"ar": "اسم البرنامج", "en": "Software name"},
	"urlLabel": {"ar": "الرابط الأساسي", "en": "Main link"},
	"url2Label": {"ar": "رابط إضافي (اختياري)", "en": "Additional link (optional)"},
	"notesLabel": {"ar": "الملاحظات", "en": "Notes"},
	"confirmDeleteTitle": {"ar": "تأكيد الحذف", "en": "Confirm delete"},
	"confirmDeleteGroup": {"ar": 'سيتم حذف المجموعة "{}" وكل ما بداخلها من فئات وبرامج. متابعة؟', "en": 'Group "{}" and everything inside it (categories and software) will be deleted. Continue?'},
	"confirmDeleteCategory": {"ar": 'سيتم حذف الفئة "{}" وكل ما بداخلها من برامج. متابعة؟', "en": 'Category "{}" and everything inside it (software) will be deleted. Continue?'},
	"confirmDeleteSoftware": {"ar": 'سيتم حذف البرنامج "{}". متابعة؟', "en": 'Software "{}" will be deleted. Continue?'},
	"settingsCategoryTitle": {"ar": "قادرين", "en": "Qadreen"},
	"settingsLanguageLabel": {"ar": "لغة الإضافة", "en": "Add-on language"},
	"settingsFollowNVDA": {"ar": "اتباع لغة NVDA", "en": "Follow NVDA language"},
	"settingsAlwaysArabic": {"ar": "العربية دائماً", "en": "Always Arabic"},
	"settingsAlwaysEnglish": {"ar": "الإنجليزية دائماً", "en": "Always English"},
	"importButton": {"ar": "استيراد بيانات", "en": "Import data"},
	"importDialogTitle": {"ar": "اختر ملف البيانات المراد استيراده", "en": "Choose the data file to import"},
	"msgImportFailed": {"ar": "تعذر قراءة الملف المحدد", "en": "Could not read the selected file"},
	"msgImportSummary": {"ar": "تم الاستيراد: {} عنصر جديد، {} نسخة إضافية بنفس الاسم برابط مختلف", "en": "Import complete: {} new items, {} additional copies with a different link"},
	"msgNoOtherGroup": {"ar": "لا توجد مجموعة أخرى لنقل إليها", "en": "There is no other group to move to"},
	"msgNoCategoryInGroup": {"ar": "هذه المجموعة لا تحتوي فئات بعد", "en": "This group has no categories yet"},
	"msgSameLocation": {"ar": "البرنامج موجود بالفعل في هذا المكان", "en": "The software is already in this location"},
	"msgMoved": {"ar": "تم النقل", "en": "Moved"},
	"moveGroupTitle": {"ar": "نقل/دمج المجموعة إلى", "en": "Move/merge group to"},
	"moveCategoryTitle": {"ar": "نقل الفئة إلى مجموعة", "en": "Move category to group"},
	"moveSoftwareGroupTitle": {"ar": "نقل البرنامج - اختر المجموعة", "en": "Move software - choose group"},
	"moveSoftwareCategoryTitle": {"ar": "نقل البرنامج - اختر الفئة", "en": "Move software - choose category"},
	"confirmMoveTitle": {"ar": "تأكيد النقل", "en": "Confirm move"},
	"confirmMoveGroup": {
		"ar": 'سيتم دمج المجموعة "{}" بالكامل داخل المجموعة "{}". العناصر المشتركة ستُستبدل ببيانات المصدر، والمجموعة الأصلية ستُحذف بعد الدمج. متابعة؟',
		"en": 'Group "{}" will be fully merged into group "{}". Shared items will be overwritten by the source data, and the original group will be deleted after merging. Continue?'
	},
	"confirmMoveCategory": {
		"ar": 'سيتم نقل الفئة "{}" من المجموعة "{}" إلى المجموعة "{}". إن وُجدت فئة بنفس الاسم هناك سيتم الدمج معها. متابعة؟',
		"en": 'Category "{}" will be moved from group "{}" to group "{}". If a category with the same name exists there, it will be merged. Continue?'
	},
	"confirmMoveSoftware": {
		"ar": 'سيتم نقل البرنامج "{}" إلى: {} / {}. إن وُجد برنامج بنفس الاسم هناك سيتم استبدال بياناته. متابعة؟',
		"en": 'Software "{}" will be moved to: {} / {}. If a software with the same name exists there, its data will be overwritten. Continue?'
	},
	"contactDeveloperButton": {"ar": "تواصل مع المطور عبر البريد الإلكتروني", "en": "Contact the developer by email"},
	"helpDialogTitle": {"ar": "مساعدة إضافة قادرين", "en": "Qadreen add-on help"},
	"helpCloseButton": {"ar": "إغلاق", "en": "Close"},
	"msgUpdateAvailable": {
		"ar": "يتوفر تحديث جديد لإضافة قادرين: الإصدار {}. يمكنك تنزيله من صفحة المشروع على GitHub.",
		"en": "A new Qadreen update is available: version {}. You can download it from the project's GitHub page."
	},
	"updateAvailableTitle": {"ar": "تحديث جديد متاح", "en": "New update available"},
	"msgUpdateConfirm": {
		"ar": "يتوفر إصدار جديد من إضافة قادرين: {}. هل تريد تنزيله وتثبيته الآن؟ بياناتك ستبقى محفوظة.",
		"en": "A new Qadreen version is available: {}. Download and install it now? Your data will be kept."
	},
	"updateInstalledTitle": {"ar": "اكتمل التحديث", "en": "Update complete"},
	"msgUpdateInstalledRestart": {
		"ar": "تم تثبيت التحديث بنجاح، وبياناتك محفوظة كما هي. يجب إعادة تشغيل NVDA لتفعيل النسخة الجديدة. إعادة التشغيل الآن؟",
		"en": "The update was installed successfully, and your data has been kept. NVDA must restart to activate the new version. Restart now?"
	},
	"msgUpdateAssetNotFound": {"ar": "تعذر إيجاد ملف التثبيت في هذا الإصدار", "en": "Could not find the installer file in this release"},
	"msgUpdateDownloadFailed": {"ar": "تعذر تنزيل التحديث", "en": "Failed to download the update"},
	"msgUpdateInstallFailed": {"ar": "تعذر تثبيت التحديث", "en": "Failed to install the update"},
	"createNewChoice": {"ar": "إنشاء جديد...", "en": "Create new..."},
	"quickAddGroupTitle": {"ar": "اختر المجموعة", "en": "Choose group"},
	"quickAddCategoryTitle": {"ar": "اختر الفئة", "en": "Choose category"},
	"msgClipboardEmpty": {"ar": "لا يوجد نص في الحافظة، انسخ الرابط أولاً", "en": "The clipboard has no text, copy the link first"},
}


def getLanguage():
	"""تحديد لغة واجهة الإضافة الحالية بناءً على إعداد المستخدم"""
	setting = config.conf["qadreen"]["language"]
	if setting == "ar":
		return "ar"
	if setting == "en":
		return "en"
	# follow: اتباع لغة NVDA الحالية
	nvdaLang = languageHandler.getLanguage()
	return "ar" if nvdaLang.startswith("ar") else "en"


HELP_TEXT = {
	"ar": """مساعدة إضافة قادرين

الاختصار العام
Insert+Control+Q: فتح نافذة الإضافة، تفتح دائماً على وضع العرض.
Insert+Control+H: فتح نافذة المساعدة هذه.
Insert+Shift+C: إضافة سريعة من أي برنامج آخر (متصفح، تليجرام، واتساب). انسخ الرابط أولاً بطريقتك المعتادة، ثم اضغط هذا الاختصار: يقرأ الرابط من الحافظة، ويطلب منك اختيار أو إنشاء المجموعة ثم الفئة، ثم يفتح نافذة إضافة برنامج بالرابط معبأً تلقائياً لتكتب الاسم والملاحظات.
Control+D: التبديل بين وضع العرض ووضع التصميم داخل النافذة.

وضع العرض (البحث والنسخ)
اكتب في مربع البحث لتصفية الفئات والبرامج فوراً (المجموعة لا تُفلتر وتبقى ظاهرة كاملة). يُعلن الناطق بعدد النتائج بعد كل حرف.
التنقل بالسهم في قائمة المجموعة يحدد المجموعة فوراً ويملأ قائمة الفئات.
اختيار فئة يملأ قائمة البرامج الخاصة بها.
التنقل بالسهم على برنامج يقرأ ملاحظاته صوتياً تلقائياً إن وُجدت (الملاحظات لا تُنسخ أبداً).
Enter على برنامج محدد: نسخ اسمه ورابطه (والرابط الإضافي إن وُجد) للحافظة، ثم إغلاق النافذة.
Control+Enter على برنامج محدد: فتح رابطه في المتصفح دون إغلاق النافذة.
Enter داخل مربع البحث نفسه: تنظيف النص المكتوب فقط مع إبقاء النتائج الحالية ظاهرة.
زر نسخ الرابط: نسخ برنامج دون إغلاق النافذة، ويسمح بتجميع أكثر من رابط (يتحول نصه إلى "إضافة إلى النسخ" بعد أول استخدام).
Escape أو زر إغلاق: إغلاق النافذة.

وضع التصميم (إدارة البيانات)
Control+N: إضافة مجموعة جديدة.
Control+Shift+N: إضافة فئة للمجموعة المحددة حالياً.
Control+F2: إضافة برنامج للفئة المحددة حالياً (الاسم، ثم الرابط الأساسي وهو إلزامي، ثم رابط إضافي اختياري، ثم الملاحظات).
F2: تعديل العنصر الذي عليه التركيز حالياً (مجموعة أو فئة أو برنامج)، بكل بياناته.
Delete: حذف العنصر الذي عليه التركيز حالياً، مع رسالة تأكيد.
Control+M: نقل أو دمج العنصر الذي عليه التركيز حالياً (مجموعة أو فئة أو برنامج) إلى مكان آخر، مع رسالة تأكيد قبل التنفيذ.
Control+O أو زر استيراد بيانات (آخر عنصر في ترتيب Tab): استيراد بيانات من ملف data.json آخر ودمجها مع بياناتك الحالية دون حذف أي شيء. العنصر المطابق تماماً (نفس المسار ونفس الرابط) يُتجاهل، والعنصر بنفس المسار لكن برابط مختلف يُضاف كنسخة منفصلة بجانب القديم.

إعدادات الإضافة
من إعدادات NVDA، فئة Qadreen: تحديد لغة واجهة الإضافة (اتباع لغة NVDA، أو عربي دائماً، أو إنجليزي دائماً)، وزر للتواصل مع المطور عبر البريد الإلكتروني.""",
	"en": """Qadreen add-on help

Global shortcut
Insert+Control+Q: Open the add-on window, always opens in View mode.
Insert+Control+H: Open this help window.
Insert+Shift+C: Quick-add from any other program (browser, Telegram, WhatsApp). First copy the link as you normally would, then press this shortcut: it reads the link from the clipboard, asks you to choose or create the group then the category, then opens the add-software window with the link already filled in so you just type the name and notes.
Control+D: Toggle between View mode and Design mode inside the window.

View mode (search and copy)
Type in the search box to filter categories and software instantly (the Group list is not filtered and stays fully visible). The screen reader announces the result count after every keystroke.
Arrow navigation in the Group list selects a group immediately and fills the Category list.
Selecting a category fills its Software list.
Arrow navigation on a software item automatically reads its notes aloud if any exist (notes are never copied).
Enter on a selected software item: copies its name and link (and additional link if present) to the clipboard, then closes the window.
Control+Enter on a selected software item: opens its link in the browser without closing the window.
Enter inside the search box itself: clears the typed text only, keeping the current results visible.
Copy link button: copies a software item without closing the window, and allows accumulating more than one link (its label changes to "Add to copy" after first use).
Escape or the Close button: closes the window.

Design mode (data management)
Control+N: add a new group.
Control+Shift+N: add a category to the currently selected group.
Control+F2: add a software item to the currently selected category (name, then a required main link, then an optional additional link, then notes).
F2: edit the currently focused item (group, category, or software), including all its data.
Delete: delete the currently focused item, with a confirmation prompt.
Control+M: move or merge the currently focused item (group, category, or software) to another location, with a confirmation prompt before it happens.
Control+O or the Import data button (last item in Tab order): import data from another data.json file and merge it with your current data without deleting anything. An item that matches exactly (same path and same link) is skipped, and an item with the same path but a different link is added as a separate copy next to the old one.

Add-on settings
From NVDA Settings, under the Qadreen category: choose the add-on's interface language (follow NVDA's language, always Arabic, or always English), and a button to contact the developer by email.""",
}


def tr(key, *args):
	"""إرجاع النص المترجم المناسب للغة الحالية، مع دعم .format إن وُجدت وسائط"""
	entry = STRINGS.get(key)
	if entry is None:
		return key
	text = entry.get(getLanguage(), entry.get("en", key))
	if args:
		return text.format(*args)
	return text


def formatResultsCount(count):
	"""إعلان صوتي بعدد نتائج البحث، بصياغة عربية صحيحة نحوياً حسب العدد"""
	if getLanguage() == "ar":
		if count == 0:
			return "لا توجد نتائج"
		if count == 1:
			return "نتيجة واحدة"
		if count == 2:
			return "نتيجتان"
		if 3 <= count <= 10:
			return "{} نتائج".format(count)
		return "{} نتيجة".format(count)
	else:
		return "1 result" if count == 1 else "{} results".format(count)


# =====================================================================
# تسجيل مواصفات الإعداد (confspec) الخاصة بالإضافة
# =====================================================================

confspec = {
	"language": 'option("follow","ar","en", default="follow")',
}
config.conf.spec["qadreen"] = confspec


def loadData():
	"""تحميل ملف data.json إلى قاموس في الذاكرة"""
	if os.path.isfile(DATA_FILE):
		try:
			with open(DATA_FILE, "r", encoding="utf-8") as f:
				return json.load(f)
		except (OSError, json.JSONDecodeError):
			return {}
	return {}


def saveData(data):
	"""حفظ القاموس الحالي إلى ملف data.json"""
	try:
		with open(DATA_FILE, "w", encoding="utf-8") as f:
			json.dump(data, f, ensure_ascii=False, indent="\t")
		return True
	except OSError:
		return False


# =====================================================================
# فحص التحديثات: مرة واحدة فقط عند كل بدء تشغيل لـNVDA، يتحقق من أحدث
# إصدار مستقر منشور على GitHub (وليس أي نسخة تجريبية أو مسودة، لأن نقطة
# نهاية "أحدث إصدار" في GitHub تستثني هذه النسخ تلقائياً)
# =====================================================================

GITHUB_LATEST_RELEASE_API = "https://api.github.com/repos/saedmohamedn2210-create/Qadreen/releases/latest"

# مكان النسخة الاحتياطية لبيانات المستخدم أثناء التحديث: خارج مجلد
# الإضافة تماماً (في مجلد المستخدم)، حتى تنجو من استبدال مجلد الإضافة
# بالكامل أثناء التثبيت، وتُستعاد تلقائياً عند أول تشغيل بعد إعادة التشغيل
UPDATE_BACKUP_PATH = os.path.join(os.path.expanduser("~"), ".qadreen_data_backup.json")


def parseVersion(versionString):
	"""تحويل نص إصدار مثل '1.2' أو 'v1.2' إلى tuple أرقام لمقارنة صحيحة"""
	parts = []
	for part in versionString.strip().lstrip("vV").split("."):
		digits = "".join(ch for ch in part if ch.isdigit())
		parts.append(int(digits) if digits else 0)
	return tuple(parts)


def restoreDataBackupIfNeeded():
	"""تُستدعى عند بدء تشغيل الإضافة: لو وُجدت نسخة احتياطية من data.json
	تركها تحديث سابق (لأن حزمة التثبيت الجديدة استبدلت data.json بنسختها
	التجريبية الافتراضية)، تُستعاد بيانات المستخدم الحقيقية فوراً، ثم تُحذف
	النسخة الاحتياطية حتى لا تُعاد مرة أخرى في المرات القادمة."""
	if not os.path.isfile(UPDATE_BACKUP_PATH):
		return
	try:
		with open(UPDATE_BACKUP_PATH, "r", encoding="utf-8") as f:
			backupData = json.load(f)
		with open(DATA_FILE, "w", encoding="utf-8") as f:
			json.dump(backupData, f, ensure_ascii=False, indent="\t")
		os.remove(UPDATE_BACKUP_PATH)
	except (OSError, json.JSONDecodeError):
		pass


def promptRestart():
	"""تُعرض بعد اكتمال التثبيت: تسأل المستخدم إن كان يريد إعادة تشغيل
	NVDA الآن لتفعيل النسخة الجديدة. تُستدعى دائماً عبر wx.CallAfter من
	الخيط الرئيسي، وتستخدم gui.mainFrame مع prePopup/postPopup كما يتطلب
	NVDA لأي نافذة modal تُعرض من سياق خارج نافذة مفتوحة فعلاً للإضافة."""
	gui.mainFrame.prePopup()
	try:
		restartNow = confirmYesNo(
			gui.mainFrame,
			tr("updateInstalledTitle"),
			tr("msgUpdateInstalledRestart")
		)
	finally:
		gui.mainFrame.postPopup()
	if restartNow:
		import core
		core.restart()


def downloadAndInstallUpdate(releaseData):
	"""تعمل داخل خيط منفصل: تنزيل حزمة التحديث، نسخ بيانات المستخدم
	الحالية احتياطياً، تثبيت الحزمة الجديدة، ثم عرض طلب إعادة التشغيل."""
	asset = None
	for a in releaseData.get("assets", []):
		if a.get("name", "").endswith(".nvda-addon"):
			asset = a
			break
	if asset is None:
		wx.CallAfter(ui.message, tr("msgUpdateAssetNotFound"))
		return

	tempPath = os.path.join(tempfile.gettempdir(), "Qadreen_update.nvda-addon")
	try:
		request = urllib.request.Request(
			asset["browser_download_url"],
			headers={"User-Agent": "Qadreen-NVDA-Addon"}
		)
		with urllib.request.urlopen(request, timeout=60) as response:
			fileData = response.read()
		with open(tempPath, "wb") as outFile:
			outFile.write(fileData)
	except Exception:
		wx.CallAfter(ui.message, tr("msgUpdateDownloadFailed"))
		return

	# نسخ بيانات المستخدم الحالية لمكان آمن خارج مجلد الإضافة قبل التثبيت،
	# لأن التثبيت سيستبدل مجلد الإضافة بالكامل بما فيه data.json التجريبي
	try:
		if os.path.isfile(DATA_FILE):
			with open(DATA_FILE, "r", encoding="utf-8") as src:
				currentDataText = src.read()
			with open(UPDATE_BACKUP_PATH, "w", encoding="utf-8") as dst:
				dst.write(currentDataText)
	except OSError:
		pass

	try:
		bundle = addonHandler.AddonBundle(tempPath)
		addonHandler.installAddonBundle(bundle)
	except Exception:
		wx.CallAfter(ui.message, tr("msgUpdateInstallFailed"))
		return

	wx.CallAfter(promptRestart)


def onUpdateFound(releaseData, latestTag):
	"""تُستدعى عبر wx.CallAfter من خيط الفحص: تعرض تأكيداً بسيطاً (نعم/لا)
	على المستخدم، وعند الموافقة فقط يبدأ التنزيل والتثبيت تلقائياً."""
	gui.mainFrame.prePopup()
	try:
		proceed = confirmYesNo(
			gui.mainFrame,
			tr("updateAvailableTitle"),
			tr("msgUpdateConfirm", latestTag)
		)
	finally:
		gui.mainFrame.postPopup()
	if proceed:
		threading.Thread(target=downloadAndInstallUpdate, args=(releaseData,), daemon=True).start()


def checkForUpdateInBackground():
	"""تعمل داخل خيط منفصل حتى لا تُجمّد NVDA أثناء انتظار الاتصال بالشبكة"""
	try:
		# تأخير بسيط حتى لا تتزاحم الرسالة الصوتية مع إعلانات بدء تشغيل NVDA
		time.sleep(8)

		try:
			addon = addonHandler.getCodeAddon()
			currentVersion = addon.manifest["version"]
		except Exception:
			return

		request = urllib.request.Request(
			GITHUB_LATEST_RELEASE_API,
			headers={"Accept": "application/vnd.github+json", "User-Agent": "Qadreen-NVDA-Addon"}
		)
		with urllib.request.urlopen(request, timeout=10) as response:
			releaseData = json.loads(response.read().decode("utf-8"))

		latestTag = releaseData.get("tag_name", "")
		if not latestTag:
			return

		if parseVersion(latestTag) > parseVersion(currentVersion):
			wx.CallAfter(onUpdateFound, releaseData, latestTag)
	except Exception:
		# فشل الاتصال بالشبكة أو أي خطأ آخر: نتجاهله بصمت تماماً، حتى لا
		# نزعج المستخدم برسائل خطأ عند غياب الإنترنت مثلاً
		pass


def mergeData(target, source):
	"""
	دمج بيانات مستوردة (source) داخل البيانات الحالية (target) دون حذف أو
	استبدال أي شيء موجود فعلاً. الهوية الكاملة (مجموعة + فئة + برنامج) هي
	التي تحدد إن كان العنصر موجوداً.
	العناصر الموجودة فقط في target تبقى كما هي.
	العناصر الموجودة فقط في source تُضاف كما هي.
	العناصر المشتركة (بنفس المسار الكامل):
	  - لو الرابط (الأساسي والإضافي) متطابق تماماً مع الموجود عندك: يُتجاهل
	    العنصر بالكامل، لا تغيير إطلاقاً.
	  - لو الرابط مختلف: لا يُستبدل القديم، بل يُضاف العنصر المستورد كنسخة
	    منفصلة بجانبه (باسم مميز، لأن نفس الاسم لا يمكن أن يتكرر حرفياً
	    داخل نفس الفئة)، فتحتفظ بالنسختين معاً لتقارن بينهما بنفسك لاحقاً.
	إرجاع: (عدد العناصر المضافة الجديدة كلياً، عدد النسخ الإضافية المُضافة
	بسبب اختلاف الرابط عند نفس المسار).
	"""
	addedCount = 0
	duplicatedCount = 0
	for groupName, categories in source.items():
		targetGroup = target.setdefault(groupName, {})
		for categoryName, softwareDict in categories.items():
			targetCategory = targetGroup.setdefault(categoryName, {})
			for softwareName, info in softwareDict.items():
				if softwareName not in targetCategory:
					targetCategory[softwareName] = info
					addedCount += 1
					continue

				existing = targetCategory[softwareName]
				sameUrl = existing.get("url", "") == info.get("url", "")
				sameUrl2 = existing.get("url2", "") == info.get("url2", "")
				if sameUrl and sameUrl2:
					# نفس المسار ونفس الرابط تماماً: تجاهل كامل
					continue

				# نفس المسار لكن الرابط مختلف: لا نستبدل، بل نضيف نسخة
				# منفصلة باسم مميز بجانب النسخة الأصلية
				newName = softwareName
				counter = 2
				while newName in targetCategory:
					newName = "{} ({})".format(softwareName, counter)
					counter += 1
				targetCategory[newName] = info
				duplicatedCount += 1
	return addedCount, duplicatedCount


def confirmYesNo(parent, title, message):
	"""نافذة تأكيد عامة (نعم/لا)، الافتراضي هو (لا) للسلامة"""
	dlg = wx.MessageDialog(
		parent,
		message,
		title,
		style=wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING
	)
	result = dlg.ShowModal() == wx.ID_YES
	dlg.Destroy()
	return result


def mergeDict(target, source):
	"""دمج قاموس مصدر داخل قاموس هدف بشكل متكرر. عند تعارض المفاتيح في أعمق
	مستوى (رابط/ملاحظات)، تُستبدل قيمة الهدف بقيمة المصدر."""
	for key, value in source.items():
		if key in target and isinstance(target[key], dict) and isinstance(value, dict):
			mergeDict(target[key], value)
		else:
			target[key] = value


class SimpleNameDialog(wx.Dialog):
	"""نافذة إدخال بسيطة تحتوي حقل نصي واحد فقط (اسم المجموعة أو الفئة)"""

	def __init__(self, parent, title, fieldLabel, initialValue=""):
		super().__init__(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE)

		sizer = wx.BoxSizer(wx.VERTICAL)

		label = wx.StaticText(self, label=fieldLabel)
		self.nameCtrl = wx.TextCtrl(self, value=initialValue)
		self.nameCtrl.SetName(fieldLabel)

		buttonsSizer = self.CreateButtonSizer(wx.OK | wx.CANCEL)

		sizer.Add(label, 0, wx.ALL, 8)
		sizer.Add(self.nameCtrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
		sizer.Add(buttonsSizer, 0, wx.ALIGN_CENTER | wx.ALL, 8)

		self.SetSizerAndFit(sizer)
		self.nameCtrl.SetFocus()
		self.nameCtrl.SelectAll()

		self.Bind(wx.EVT_BUTTON, self.onOK, id=wx.ID_OK)

	def onOK(self, event):
		if not self.nameCtrl.GetValue().strip():
			ui.message(tr("msgNameRequired"))
			self.nameCtrl.SetFocus()
			return
		event.Skip()

	def GetValueEntered(self):
		return self.nameCtrl.GetValue().strip()


class SoftwareDialog(wx.Dialog):
	"""نافذة إضافة أو تعديل برنامج: الاسم، الرابط الأساسي، رابط إضافي اختياري، الملاحظات"""

	def __init__(self, parent, title, name="", url="", url2="", notes=""):
		super().__init__(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE)

		sizer = wx.BoxSizer(wx.VERTICAL)

		nameLabel = wx.StaticText(self, label=tr("softwareNameLabel"))
		self.nameCtrl = wx.TextCtrl(self, value=name)
		self.nameCtrl.SetName(tr("softwareNameLabel"))

		urlLabel = wx.StaticText(self, label=tr("urlLabel"))
		self.urlCtrl = wx.TextCtrl(self, value=url)
		self.urlCtrl.SetName(tr("urlLabel"))

		url2Label = wx.StaticText(self, label=tr("url2Label"))
		self.url2Ctrl = wx.TextCtrl(self, value=url2)
		self.url2Ctrl.SetName(tr("url2Label"))

		notesLabel = wx.StaticText(self, label=tr("notesLabel"))
		self.notesCtrl = wx.TextCtrl(self, value=notes)
		self.notesCtrl.SetName(tr("notesLabel"))

		buttonsSizer = self.CreateButtonSizer(wx.OK | wx.CANCEL)

		for lbl, ctrl in (
			(nameLabel, self.nameCtrl),
			(urlLabel, self.urlCtrl),
			(url2Label, self.url2Ctrl),
			(notesLabel, self.notesCtrl),
		):
			sizer.Add(lbl, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
			sizer.Add(ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

		sizer.Add(buttonsSizer, 0, wx.ALIGN_CENTER | wx.ALL, 8)

		self.SetSizerAndFit(sizer)
		self.nameCtrl.SetFocus()
		self.nameCtrl.SelectAll()

		self.Bind(wx.EVT_BUTTON, self.onOK, id=wx.ID_OK)

	def onOK(self, event):
		if not self.nameCtrl.GetValue().strip():
			ui.message(tr("msgSoftwareNameRequired"))
			self.nameCtrl.SetFocus()
			return
		if not self.urlCtrl.GetValue().strip():
			ui.message(tr("msgUrlRequired"))
			self.urlCtrl.SetFocus()
			return
		event.Skip()

	def GetValuesEntered(self):
		return (
			self.nameCtrl.GetValue().strip(),
			self.urlCtrl.GetValue().strip(),
			self.url2Ctrl.GetValue().strip(),
			self.notesCtrl.GetValue().strip(),
		)


class ChoiceDialog(wx.Dialog):
	"""نافذة اختيار عنصر واحد من قائمة (تُستخدم لاختيار وجهة النقل)"""

	def __init__(self, parent, title, label, choices):
		super().__init__(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)

		sizer = wx.BoxSizer(wx.VERTICAL)

		lbl = wx.StaticText(self, label=label)
		self.listBox = wx.ListBox(self, choices=choices, style=wx.LB_SINGLE)
		self.listBox.SetName(label)
		if choices:
			self.listBox.SetSelection(0)

		buttonsSizer = self.CreateButtonSizer(wx.OK | wx.CANCEL)

		sizer.Add(lbl, 0, wx.ALL, 8)
		sizer.Add(self.listBox, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
		sizer.Add(buttonsSizer, 0, wx.ALIGN_CENTER | wx.ALL, 8)

		self.SetSizerAndFit(sizer)
		self.SetSize((360, 320))
		self.listBox.SetFocus()

		self.Bind(wx.EVT_BUTTON, self.onOK, id=wx.ID_OK)
		self.Bind(wx.EVT_LISTBOX_DCLICK, self.onDClick)

	def onOK(self, event):
		if self.listBox.GetSelection() == wx.NOT_FOUND:
			ui.message(tr("msgSelectItemFirst"))
			return
		event.Skip()

	def onDClick(self, event):
		self.EndModal(wx.ID_OK)

	def GetSelectedChoice(self):
		return self.listBox.GetStringSelection()


class HelpDialog(wx.Dialog):
	"""نافذة مساعدة للقراءة فقط، تعرض شرح كل الاختصارات والوظائف باللغة الحالية للإضافة"""

	def __init__(self, parent):
		super().__init__(
			parent,
			title=tr("helpDialogTitle"),
			style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
		)

		sizer = wx.BoxSizer(wx.VERTICAL)

		text = HELP_TEXT.get(getLanguage(), HELP_TEXT["en"])
		self.textCtrl = wx.TextCtrl(
			self, value=text,
			style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_BESTWRAP
		)
		self.textCtrl.SetName(tr("helpDialogTitle"))

		closeButton = wx.Button(self, id=wx.ID_CLOSE, label=tr("helpCloseButton"))

		sizer.Add(self.textCtrl, 1, wx.EXPAND | wx.ALL, 8)
		sizer.Add(closeButton, 0, wx.ALIGN_CENTER | wx.BOTTOM, 8)

		self.SetSizer(sizer)
		self.SetSize((640, 520))
		self.CentreOnScreen()

		closeButton.Bind(wx.EVT_BUTTON, lambda evt: self.Close())
		self.Bind(wx.EVT_CHAR_HOOK, self.onCharHook)

		wx.CallAfter(self.textCtrl.SetFocus)

	def onCharHook(self, event):
		if event.GetKeyCode() == wx.WXK_ESCAPE:
			self.Close()
		else:
			event.Skip()


class SearchDialog(wx.Dialog):
	"""النافذة الرئيسية للإضافة: وضع العرض (بحث ونسخ) ووضع التصميم (إدارة بيانات)"""

	def __init__(self, parent, data, startMode="view"):
		super().__init__(
			parent,
			title=tr("dialogTitleDesign") if startMode == "design" else tr("dialogTitleView"),
			style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
		)
		self.data = data
		# قائمة الروابط المجمعة للنسخ المتعدد: كل عنصر (اسم البرنامج، الرابط)
		self.copiedItems = []
		self._notesTimer = None
		# الوضع الحالي: "view" وضع العرض، أو "design" وضع التصميم
		self.mode = startMode

		self._buildUI()
		self._bindEvents()
		self._populateGroups()

		if self.mode == "design":
			# نُنشئ النافذة مباشرة في وضع التصميم (تُستخدم مع الإضافة
			# السريعة من الحافظة)، بدون المرور بوضع العرض أولاً وبدون
			# إعلان "وضع التصميم" الذي يوحي بدخول عام للتصفح
			self.searchLabel.Hide()
			self.searchCtrl.Hide()
			self.copyButton.Hide()
			self.importButton.Show()

		self.SetSize((560, 420))
		self.CentreOnScreen()

	# ---------------------------------------------------------------
	# بناء الواجهة
	# ---------------------------------------------------------------

	def _buildUI(self):
		mainSizer = wx.BoxSizer(wx.VERTICAL)

		self.searchLabel = wx.StaticText(self, label=tr("searchLabel"))
		self.searchCtrl = wx.TextCtrl(self)
		self.searchCtrl.SetName(tr("searchCtrlName"))

		listsSizer = wx.BoxSizer(wx.HORIZONTAL)

		groupSizer = wx.BoxSizer(wx.VERTICAL)
		groupLabel = wx.StaticText(self, label=tr("groupLabel"))
		self.groupList = wx.ListBox(self, style=wx.LB_SINGLE)
		self.groupList.SetName(tr("groupListName"))
		groupSizer.Add(groupLabel, 0, wx.BOTTOM, 4)
		groupSizer.Add(self.groupList, 1, wx.EXPAND)

		categorySizer = wx.BoxSizer(wx.VERTICAL)
		categoryLabel = wx.StaticText(self, label=tr("categoryLabel"))
		self.categoryList = wx.ListBox(self, style=wx.LB_SINGLE)
		self.categoryList.SetName(tr("categoryListName"))
		categorySizer.Add(categoryLabel, 0, wx.BOTTOM, 4)
		categorySizer.Add(self.categoryList, 1, wx.EXPAND)

		softwareSizer = wx.BoxSizer(wx.VERTICAL)
		softwareLabel = wx.StaticText(self, label=tr("softwareLabel"))
		self.softwareList = wx.ListBox(self, style=wx.LB_SINGLE)
		self.softwareList.SetName(tr("softwareListName"))
		softwareSizer.Add(softwareLabel, 0, wx.BOTTOM, 4)
		softwareSizer.Add(self.softwareList, 1, wx.EXPAND)

		listsSizer.Add(groupSizer, 1, wx.EXPAND | wx.RIGHT, 6)
		listsSizer.Add(categorySizer, 1, wx.EXPAND | wx.RIGHT, 6)
		listsSizer.Add(softwareSizer, 1, wx.EXPAND)

		buttonsSizer = wx.BoxSizer(wx.HORIZONTAL)
		self.copyButton = wx.Button(self, label=tr("copyButton"))
		self.closeButton = wx.Button(self, label=tr("closeButton"))
		self.importButton = wx.Button(self, label=tr("importButton"))
		self.importButton.Hide()
		buttonsSizer.Add(self.copyButton, 0, wx.RIGHT, 8)
		buttonsSizer.Add(self.closeButton, 0, wx.RIGHT, 8)
		buttonsSizer.Add(self.importButton, 0)

		mainSizer.Add(self.searchLabel, 0, wx.LEFT | wx.TOP, 8)
		mainSizer.Add(self.searchCtrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)
		mainSizer.Add(listsSizer, 1, wx.EXPAND | wx.ALL, 8)
		mainSizer.Add(buttonsSizer, 0, wx.ALIGN_LEFT | wx.LEFT | wx.BOTTOM, 8)

		self.SetSizer(mainSizer)

	def _bindEvents(self):
		self.searchCtrl.Bind(wx.EVT_TEXT, self.onSearchTextChanged)
		self.groupList.Bind(wx.EVT_LISTBOX, self.onGroupSelected)
		self.categoryList.Bind(wx.EVT_LISTBOX, self.onCategorySelected)
		self.softwareList.Bind(wx.EVT_LISTBOX, self.onSoftwareSelected)
		self.softwareList.Bind(wx.EVT_KEY_DOWN, self.onSoftwareKeyDown)
		self.copyButton.Bind(wx.EVT_BUTTON, self.onCopyButton)
		self.closeButton.Bind(wx.EVT_BUTTON, lambda evt: self.Close())
		self.importButton.Bind(wx.EVT_BUTTON, lambda evt: self._importData())
		self.Bind(wx.EVT_CHAR_HOOK, self.onCharHook)

	# ---------------------------------------------------------------
	# تعبئة القوائم - وضع التصفح العادي (بدون بحث)
	# ---------------------------------------------------------------

	def _populateGroups(self):
		self.groupList.Clear()
		for groupName in sorted(self.data.keys()):
			self.groupList.Append(groupName)
		self.categoryList.Clear()
		self.softwareList.Clear()

	def _populateCategoriesForGroup(self, groupName):
		self.categoryList.Clear()
		self.softwareList.Clear()
		categories = self.data.get(groupName, {})
		for categoryName in sorted(categories.keys()):
			self.categoryList.Append(categoryName, (groupName, categoryName))

	def _populateSoftwareForCategory(self, groupName, categoryName):
		self.softwareList.Clear()
		software = self.data.get(groupName, {}).get(categoryName, {})
		for softwareName in sorted(software.keys()):
			self.softwareList.Append(softwareName, (groupName, categoryName, softwareName))

	# ---------------------------------------------------------------
	# تعبئة القوائم - وضع البحث (يشمل الفئات والبرامج، يستثني المجموعة)
	# ---------------------------------------------------------------

	def _populateFromSearch(self, query):
		self.categoryList.Clear()
		self.softwareList.Clear()

		addedCategories = set()
		# نجمع كل النتائج أولاً، ثم نرتبها أبجدياً قبل عرضها
		categoryEntries = []  # (categoryLabel, key)
		softwareEntries = []  # (softwareLabel, clientData)

		for groupName in sorted(self.data.keys()):
			categories = self.data[groupName]
			for categoryName in sorted(categories.keys()):
				softwareDict = categories[categoryName]
				categoryMatches = query in categoryName.lower()
				matchedSoftware = sorted(
					name for name in softwareDict.keys()
					if query in name.lower() or categoryMatches
				)
				if matchedSoftware:
					key = (groupName, categoryName)
					categoryLabel = "{} ({})".format(categoryName, groupName)
					if key not in addedCategories:
						categoryEntries.append((categoryLabel, key))
						addedCategories.add(key)
					for softwareName in matchedSoftware:
						# نُضيف المجموعة والفئة لاسم البرنامج الظاهر في نتائج
						# البحث، لأن نفس اسم البرنامج قد يتكرر في أكثر من
						# مجموعة (مثال: Firefox في Android وiPhone معاً)
						softwareLabel = "{} — {} / {}".format(softwareName, groupName, categoryName)
						softwareEntries.append((softwareLabel, (groupName, categoryName, softwareName)))

		for categoryLabel, key in sorted(categoryEntries, key=lambda item: item[0]):
			self.categoryList.Append(categoryLabel, key)
		for softwareLabel, clientData in sorted(softwareEntries, key=lambda item: item[0]):
			self.softwareList.Append(softwareLabel, clientData)

	# ---------------------------------------------------------------
	# الأحداث العامة
	# ---------------------------------------------------------------

	def onSearchTextChanged(self, event):
		if self.mode == "design":
			return
		query = self.searchCtrl.GetValue().strip().lower()
		if not query:
			self._populateGroups()
		else:
			self._populateFromSearch(query)
			count = self.softwareList.GetCount()
			ui.message(formatResultsCount(count))

	def onGroupSelected(self, event):
		groupName = self.groupList.GetStringSelection()
		if groupName:
			self._populateCategoriesForGroup(groupName)

	def onCategorySelected(self, event):
		index = self.categoryList.GetSelection()
		if index == wx.NOT_FOUND:
			return
		groupCategoryData = self.categoryList.GetClientData(index)
		if not groupCategoryData:
			return
		groupName, categoryName = groupCategoryData

		# إن كنا في وضع البحث، لا نعيد تعبئة قائمة البرامج بكل عناصر
		# الفئة، بل نُبقي فقط على العناصر المطابقة الظاهرة أصلاً.
		if not self.searchCtrl.GetValue().strip():
			self._populateSoftwareForCategory(groupName, categoryName)
			# مزامنة تحديد المجموعة في قائمة Group
			groupIndex = self.groupList.FindString(groupName)
			if groupIndex != wx.NOT_FOUND:
				self.groupList.SetSelection(groupIndex)

	def onSoftwareSelected(self, event):
		# نقرأ الملاحظات صوتياً فقط في وضع العرض، ولا نستخدمها أبداً عند النسخ
		if self._notesTimer is not None:
			self._notesTimer.Stop()
			self._notesTimer = None

		if self.mode != "view":
			return
		index = self.softwareList.GetSelection()
		if index == wx.NOT_FOUND:
			return
		clientData = self.softwareList.GetClientData(index)
		if not clientData:
			return
		groupName, categoryName, softwareName = clientData
		info = self.data.get(groupName, {}).get(categoryName, {}).get(softwareName, {})
		notes = info.get("notes", "").strip()
		if notes:
			# تأخير حقيقي (200 ملي ثانية) قبل نطق الملاحظات، حتى يكتمل
			# إعلان NVDA الطبيعي لاسم العنصر أولاً. CallAfter وحدها لم
			# تكن كافية لأنها فقط تنتظر دورة الأحداث التالية، وقد تسبق
			# إعلان NVDA الفعلي. نُلغي أي مؤقت سابق لم يُنفَّذ بعد حتى لا
			# تُقرأ ملاحظات عنصر سابق أثناء التنقل السريع بالأسهم.
			self._notesTimer = wx.CallLater(200, ui.message, notes)

	def onSoftwareKeyDown(self, event):
		# لم يعد الاعتماد على هذا المعالج لمفتاح Enter، لأن نافذة الحوار
		# تعترضه قبل وصوله هنا (انظر onCharHook). أُبقيه لأي مفاتيح أخرى مستقبلية.
		event.Skip()

	def onCharHook(self, event):
		keyCode = event.GetKeyCode()

		if keyCode == wx.WXK_ESCAPE:
			self.Close()
			return

		if event.ControlDown() and not event.ShiftDown() and keyCode == ord("D"):
			self._toggleMode()
			return

		# معالجة Enter في وضع العرض هنا مباشرة، لأن نافذة الحوار تعترض
		# مفتاح Enter (بحثاً عن زر افتراضي) قبل أن يصل لقائمة البرامج
		if self.mode == "view" and self.FindFocus() == self.softwareList:
			if keyCode in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
				if event.ControlDown():
					self._openSelectedLink()
				else:
					self._copySelectedAndClose()
				return

		# Enter داخل مربع البحث نفسه: تنظيف النص المكتوب فقط، مع إبقاء
		# نتائج البحث الحالية ظاهرة في Category وSoftware كما هي (نستخدم
		# ChangeValue بدل SetValue لأنها لا تُطلق حدث EVT_TEXT، فلا تُعاد
		# تعبئة القوائم بكل المجموعات من جديد)
		if self.mode == "view" and self.FindFocus() == self.searchCtrl:
			if keyCode in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
				self.searchCtrl.ChangeValue("")
				return

		if self.mode == "design":
			if event.ControlDown() and event.ShiftDown() and keyCode == ord("N"):
				self._addCategory()
				return
			if event.ControlDown() and not event.ShiftDown() and keyCode == ord("N"):
				self._addGroup()
				return
			if event.ControlDown() and keyCode == wx.WXK_F2:
				self._addSoftware()
				return
			if keyCode == wx.WXK_F2:
				self._editFocusedItem()
				return
			if keyCode == wx.WXK_DELETE:
				self._deleteFocusedItem()
				return
			if event.ControlDown() and not event.ShiftDown() and keyCode == ord("O"):
				self._importData()
				return
			if event.ControlDown() and not event.ShiftDown() and keyCode == ord("M"):
				self._moveFocusedItem()
				return

		event.Skip()

	def onCopyButton(self, event):
		item = self._getSelectedSoftwareItem()
		if not item:
			ui.message(tr("msgNoSoftwareSelected"))
			return
		groupName, categoryName, softwareName, url, url2 = item
		self.copiedItems.append((softwareName, url, url2))
		self._writeClipboard()
		self.copyButton.SetLabel(tr("addToCopyButton"))
		ui.message(tr("msgCopied"))

	# ---------------------------------------------------------------
	# التبديل بين وضع العرض ووضع التصميم
	# ---------------------------------------------------------------

	def _toggleMode(self):
		self.searchCtrl.SetValue("")
		if self.mode == "view":
			self.mode = "design"
			self.SetTitle(tr("dialogTitleDesign"))
			self.searchLabel.Hide()
			self.searchCtrl.Hide()
			self.copyButton.Hide()
			self.importButton.Show()
			ui.message(tr("msgDesignMode"))
		else:
			self.mode = "view"
			self.SetTitle(tr("dialogTitleView"))
			self.searchLabel.Show()
			self.searchCtrl.Show()
			self.copyButton.Show()
			self.importButton.Hide()
			ui.message(tr("msgViewMode"))

		self._populateGroups()
		self.Layout()

		focusTarget = self.groupList if self.mode == "design" else self.searchCtrl
		wx.CallAfter(focusTarget.SetFocus)

	# ---------------------------------------------------------------
	# وضع التصميم: إضافة عناصر جديدة
	# ---------------------------------------------------------------

	def _addGroup(self):
		dlg = SimpleNameDialog(self, tr("addGroupTitle"), tr("groupNameLabel"))
		if dlg.ShowModal() == wx.ID_OK:
			name = dlg.GetValueEntered()
			if name in self.data:
				ui.message(tr("msgNameExists"))
			else:
				self.data[name] = {}
				saveData(self.data)
				self._populateGroups()
				self._selectAndFocus(self.groupList, name)
				ui.message(tr("msgAdded"))
		dlg.Destroy()

	def _addCategory(self):
		groupIndex = self.groupList.GetSelection()
		if groupIndex == wx.NOT_FOUND:
			ui.message(tr("msgSelectGroupFirst"))
			return
		groupName = self.groupList.GetString(groupIndex)

		dlg = SimpleNameDialog(self, tr("addCategoryTitle"), tr("categoryNameLabel"))
		if dlg.ShowModal() == wx.ID_OK:
			name = dlg.GetValueEntered()
			if name in self.data.get(groupName, {}):
				ui.message(tr("msgNameExistsInGroup"))
			else:
				self.data.setdefault(groupName, {})[name] = {}
				saveData(self.data)
				self._populateCategoriesForGroup(groupName)
				self._selectAndFocus(self.categoryList, name)
				ui.message(tr("msgAdded"))
		dlg.Destroy()

	def _addSoftware(self):
		groupIndex = self.groupList.GetSelection()
		categoryIndex = self.categoryList.GetSelection()
		if groupIndex == wx.NOT_FOUND or categoryIndex == wx.NOT_FOUND:
			ui.message(tr("msgSelectGroupAndCategoryFirst"))
			return
		groupName = self.groupList.GetString(groupIndex)
		categoryName = self.categoryList.GetString(categoryIndex)

		dlg = SoftwareDialog(self, tr("addSoftwareTitle"))
		if dlg.ShowModal() == wx.ID_OK:
			name, url, url2, notes = dlg.GetValuesEntered()
			softwareDict = self.data.setdefault(groupName, {}).setdefault(categoryName, {})
			if name in softwareDict:
				ui.message(tr("msgNameExistsInCategory"))
			else:
				softwareDict[name] = {"url": url, "url2": url2, "notes": notes}
				saveData(self.data)
				self._populateSoftwareForCategory(groupName, categoryName)
				self._selectAndFocus(self.softwareList, name)
				ui.message(tr("msgAdded"))
		dlg.Destroy()

	# ---------------------------------------------------------------
	# وضع التصميم: تعديل عناصر موجودة
	# ---------------------------------------------------------------

	def _editFocusedItem(self):
		focused = self.FindFocus()
		if focused == self.groupList:
			self._editGroup()
		elif focused == self.categoryList:
			self._editCategory()
		elif focused == self.softwareList:
			self._editSoftware()
		else:
			ui.message(tr("msgSelectItemFirst"))

	def _editGroup(self):
		index = self.groupList.GetSelection()
		if index == wx.NOT_FOUND:
			ui.message(tr("msgNoGroupSelected"))
			return
		oldName = self.groupList.GetString(index)

		dlg = SimpleNameDialog(self, tr("editGroupTitle"), tr("groupNameLabel"), initialValue=oldName)
		if dlg.ShowModal() == wx.ID_OK:
			newName = dlg.GetValueEntered()
			if newName != oldName:
				if newName in self.data:
					ui.message(tr("msgNameExists"))
				else:
					reordered = {}
					for key, value in self.data.items():
						reordered[newName if key == oldName else key] = value
					self.data.clear()
					self.data.update(reordered)
					saveData(self.data)
					self._populateGroups()
					self._selectAndFocus(self.groupList, newName)
					ui.message(tr("msgEdited"))
		dlg.Destroy()

	def _editCategory(self):
		groupIndex = self.groupList.GetSelection()
		categoryIndex = self.categoryList.GetSelection()
		if groupIndex == wx.NOT_FOUND or categoryIndex == wx.NOT_FOUND:
			ui.message(tr("msgNoCategorySelected"))
			return
		groupName = self.groupList.GetString(groupIndex)
		oldName = self.categoryList.GetString(categoryIndex)

		dlg = SimpleNameDialog(self, tr("editCategoryTitle"), tr("categoryNameLabel"), initialValue=oldName)
		if dlg.ShowModal() == wx.ID_OK:
			newName = dlg.GetValueEntered()
			if newName != oldName:
				categories = self.data.get(groupName, {})
				if newName in categories:
					ui.message(tr("msgNameExistsInGroup"))
				else:
					reordered = {}
					for key, value in categories.items():
						reordered[newName if key == oldName else key] = value
					self.data[groupName] = reordered
					saveData(self.data)
					self._populateCategoriesForGroup(groupName)
					self._selectAndFocus(self.categoryList, newName)
					ui.message(tr("msgEdited"))
		dlg.Destroy()

	def _editSoftware(self):
		groupIndex = self.groupList.GetSelection()
		categoryIndex = self.categoryList.GetSelection()
		softwareIndex = self.softwareList.GetSelection()
		if groupIndex == wx.NOT_FOUND or categoryIndex == wx.NOT_FOUND or softwareIndex == wx.NOT_FOUND:
			ui.message(tr("msgNoSoftwareSelected"))
			return
		groupName = self.groupList.GetString(groupIndex)
		categoryName = self.categoryList.GetString(categoryIndex)
		oldName = self.softwareList.GetString(softwareIndex)
		info = self.data.get(groupName, {}).get(categoryName, {}).get(oldName, {})

		dlg = SoftwareDialog(
			self, tr("editSoftwareTitle"),
			name=oldName, url=info.get("url", ""), url2=info.get("url2", ""), notes=info.get("notes", "")
		)
		if dlg.ShowModal() == wx.ID_OK:
			newName, url, url2, notes = dlg.GetValuesEntered()
			softwareDict = self.data[groupName][categoryName]
			if newName != oldName and newName in softwareDict:
				ui.message(tr("msgNameExistsInCategory"))
			else:
				if newName != oldName:
					reordered = {}
					for key, value in softwareDict.items():
						if key == oldName:
							reordered[newName] = {"url": url, "url2": url2, "notes": notes}
						else:
							reordered[key] = value
					self.data[groupName][categoryName] = reordered
				else:
					softwareDict[oldName] = {"url": url, "url2": url2, "notes": notes}
				saveData(self.data)
				self._populateSoftwareForCategory(groupName, categoryName)
				self._selectAndFocus(self.softwareList, newName)
				ui.message(tr("msgEdited"))
		dlg.Destroy()

	# ---------------------------------------------------------------
	# وضع التصميم: حذف عناصر
	# ---------------------------------------------------------------

	def _deleteFocusedItem(self):
		focused = self.FindFocus()
		if focused == self.groupList:
			self._deleteGroup()
		elif focused == self.categoryList:
			self._deleteCategory()
		elif focused == self.softwareList:
			self._deleteSoftware()
		else:
			ui.message(tr("msgSelectItemFirst"))

	def _deleteGroup(self):
		index = self.groupList.GetSelection()
		if index == wx.NOT_FOUND:
			ui.message(tr("msgNoGroupSelected"))
			return
		name = self.groupList.GetString(index)
		if confirmYesNo(self, tr("confirmDeleteTitle"), tr("confirmDeleteGroup", name)):
			del self.data[name]
			saveData(self.data)
			self._populateGroups()
			self.groupList.SetFocus()
			ui.message(tr("msgDeleted"))

	def _deleteCategory(self):
		groupIndex = self.groupList.GetSelection()
		categoryIndex = self.categoryList.GetSelection()
		if groupIndex == wx.NOT_FOUND or categoryIndex == wx.NOT_FOUND:
			ui.message(tr("msgNoCategorySelected"))
			return
		groupName = self.groupList.GetString(groupIndex)
		name = self.categoryList.GetString(categoryIndex)
		if confirmYesNo(self, tr("confirmDeleteTitle"), tr("confirmDeleteCategory", name)):
			del self.data[groupName][name]
			saveData(self.data)
			self._populateCategoriesForGroup(groupName)
			self.categoryList.SetFocus()
			ui.message(tr("msgDeleted"))

	def _deleteSoftware(self):
		groupIndex = self.groupList.GetSelection()
		categoryIndex = self.categoryList.GetSelection()
		softwareIndex = self.softwareList.GetSelection()
		if groupIndex == wx.NOT_FOUND or categoryIndex == wx.NOT_FOUND or softwareIndex == wx.NOT_FOUND:
			ui.message(tr("msgNoSoftwareSelected"))
			return
		groupName = self.groupList.GetString(groupIndex)
		categoryName = self.categoryList.GetString(categoryIndex)
		name = self.softwareList.GetString(softwareIndex)
		if confirmYesNo(self, tr("confirmDeleteTitle"), tr("confirmDeleteSoftware", name)):
			del self.data[groupName][categoryName][name]
			saveData(self.data)
			self._populateSoftwareForCategory(groupName, categoryName)
			self.softwareList.SetFocus()
			ui.message(tr("msgDeleted"))

	def _selectAndFocus(self, listBox, text):
		index = listBox.FindString(text)
		if index != wx.NOT_FOUND:
			listBox.SetSelection(index)
			listBox.SetFocus()

	# ---------------------------------------------------------------
	# وضع التصميم: نقل/دمج عناصر (مجموعة، فئة، برنامج)
	# ---------------------------------------------------------------

	def _pickFromList(self, title, label, choices):
		dlg = ChoiceDialog(self, title, label, choices)
		result = None
		if dlg.ShowModal() == wx.ID_OK:
			result = dlg.GetSelectedChoice()
		dlg.Destroy()
		return result

	def _askName(self, title, label):
		dlg = SimpleNameDialog(self, title, label)
		result = None
		if dlg.ShowModal() == wx.ID_OK:
			result = dlg.GetValueEntered()
		dlg.Destroy()
		return result

	def _pickOrCreate(self, dialogTitle, label, choices, createNewLabel, createTitle, createLabel):
		result = self._pickFromList(dialogTitle, label, choices)
		if result is None:
			return None
		if result == createNewLabel:
			return self._askName(createTitle, createLabel)
		return result

	# ---------------------------------------------------------------
	# إضافة سريعة من الحافظة (Insert+Shift+C من أي برنامج آخر): نفس
	# نوافذ وضع التصميم المعتادة تماماً، بالرابط معبأً تلقائياً
	# ---------------------------------------------------------------

	def runQuickAdd(self, url, closeWhenDone=True):
		createNewLabel = tr("createNewChoice")

		groupChoices = [createNewLabel] + sorted(self.data.keys())
		groupName = self._pickOrCreate(
			tr("quickAddGroupTitle"), tr("groupLabel"), groupChoices,
			createNewLabel, tr("addGroupTitle"), tr("groupNameLabel")
		)
		if groupName is None:
			if closeWhenDone:
				self.Close()
			return

		if groupName not in self.data:
			# مجموعة جديدة كلياً: فئاتها فارغة أصلاً، فنتخطى القائمة
			# مباشرة لمربع كتابة اسم الفئة الجديدة
			categoryName = self._askName(tr("addCategoryTitle"), tr("categoryNameLabel"))
		else:
			categoryChoices = [createNewLabel] + sorted(self.data.get(groupName, {}).keys())
			categoryName = self._pickOrCreate(
				tr("quickAddCategoryTitle"), tr("categoryLabel"), categoryChoices,
				createNewLabel, tr("addCategoryTitle"), tr("categoryNameLabel")
			)
		if categoryName is None:
			if closeWhenDone:
				self.Close()
			return

		dlg = SoftwareDialog(self, tr("addSoftwareTitle"), url=url)
		if dlg.ShowModal() == wx.ID_OK:
			name, finalUrl, url2, notes = dlg.GetValuesEntered()
			softwareDict = self.data.setdefault(groupName, {}).setdefault(categoryName, {})
			softwareDict[name] = {"url": finalUrl, "url2": url2, "notes": notes}
			saveData(self.data)
			ui.message(tr("msgAdded"))
		dlg.Destroy()

		if closeWhenDone:
			self.Close()

	def _moveFocusedItem(self):
		focused = self.FindFocus()
		if focused == self.groupList:
			self._moveGroup()
		elif focused == self.categoryList:
			self._moveCategory()
		elif focused == self.softwareList:
			self._moveSoftware()
		else:
			ui.message(tr("msgSelectItemFirst"))

	def _moveGroup(self):
		index = self.groupList.GetSelection()
		if index == wx.NOT_FOUND:
			ui.message(tr("msgNoGroupSelected"))
			return
		sourceName = self.groupList.GetString(index)

		choices = sorted(name for name in self.data.keys() if name != sourceName)
		if not choices:
			ui.message(tr("msgNoOtherGroup"))
			return

		targetName = self._pickFromList(tr("moveGroupTitle"), tr("groupLabel"), choices)
		if targetName is None:
			return

		message = tr("confirmMoveGroup", sourceName, targetName)
		if confirmYesNo(self, tr("confirmMoveTitle"), message):
			mergeDict(self.data[targetName], self.data[sourceName])
			del self.data[sourceName]
			saveData(self.data)
			self._populateGroups()
			self._selectAndFocus(self.groupList, targetName)
			ui.message(tr("msgMoved"))

	def _moveCategory(self):
		groupIndex = self.groupList.GetSelection()
		categoryIndex = self.categoryList.GetSelection()
		if groupIndex == wx.NOT_FOUND or categoryIndex == wx.NOT_FOUND:
			ui.message(tr("msgNoCategorySelected"))
			return
		sourceGroup = self.groupList.GetString(groupIndex)
		categoryName = self.categoryList.GetString(categoryIndex)

		choices = sorted(name for name in self.data.keys() if name != sourceGroup)
		if not choices:
			ui.message(tr("msgNoOtherGroup"))
			return

		targetGroup = self._pickFromList(tr("moveCategoryTitle"), tr("groupLabel"), choices)
		if targetGroup is None:
			return

		message = tr("confirmMoveCategory", categoryName, sourceGroup, targetGroup)
		if confirmYesNo(self, tr("confirmMoveTitle"), message):
			targetCategories = self.data.setdefault(targetGroup, {})
			if categoryName in targetCategories:
				mergeDict(targetCategories[categoryName], self.data[sourceGroup][categoryName])
			else:
				targetCategories[categoryName] = self.data[sourceGroup][categoryName]
			del self.data[sourceGroup][categoryName]
			saveData(self.data)
			self._populateCategoriesForGroup(sourceGroup)
			ui.message(tr("msgMoved"))

	def _moveSoftware(self):
		groupIndex = self.groupList.GetSelection()
		categoryIndex = self.categoryList.GetSelection()
		softwareIndex = self.softwareList.GetSelection()
		if groupIndex == wx.NOT_FOUND or categoryIndex == wx.NOT_FOUND or softwareIndex == wx.NOT_FOUND:
			ui.message(tr("msgNoSoftwareSelected"))
			return
		sourceGroup = self.groupList.GetString(groupIndex)
		sourceCategory = self.categoryList.GetString(categoryIndex)
		softwareName = self.softwareList.GetString(softwareIndex)

		groupChoices = sorted(self.data.keys())
		targetGroup = self._pickFromList(tr("moveSoftwareGroupTitle"), tr("groupLabel"), groupChoices)
		if targetGroup is None:
			return

		categoryChoices = sorted(self.data.get(targetGroup, {}).keys())
		if not categoryChoices:
			ui.message(tr("msgNoCategoryInGroup"))
			return

		targetCategory = self._pickFromList(tr("moveSoftwareCategoryTitle"), tr("categoryLabel"), categoryChoices)
		if targetCategory is None:
			return

		if targetGroup == sourceGroup and targetCategory == sourceCategory:
			ui.message(tr("msgSameLocation"))
			return

		message = tr("confirmMoveSoftware", softwareName, targetGroup, targetCategory)
		if confirmYesNo(self, tr("confirmMoveTitle"), message):
			info = self.data[sourceGroup][sourceCategory][softwareName]
			self.data[targetGroup][targetCategory][softwareName] = info
			del self.data[sourceGroup][sourceCategory][softwareName]
			saveData(self.data)
			self._populateSoftwareForCategory(sourceGroup, sourceCategory)
			ui.message(tr("msgMoved"))

	# ---------------------------------------------------------------
	# وضع التصميم: استيراد بيانات من ملف data.json آخر (دمج بدون حذف)
	# ---------------------------------------------------------------

	def _importData(self):
		dlg = wx.FileDialog(
			self,
			message=tr("importDialogTitle"),
			wildcard="data.json|data.json",
			style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
		)
		if dlg.ShowModal() == wx.ID_OK:
			path = dlg.GetPath()
			importedData = None
			try:
				with open(path, "r", encoding="utf-8") as f:
					importedData = json.load(f)
			except (OSError, json.JSONDecodeError):
				importedData = None

			if not isinstance(importedData, dict):
				ui.message(tr("msgImportFailed"))
			else:
				addedCount, duplicatedCount = mergeData(self.data, importedData)
				saveData(self.data)
				self._populateGroups()
				ui.message(tr("msgImportSummary", addedCount, duplicatedCount))
		dlg.Destroy()

	# ---------------------------------------------------------------
	# أدوات مساعدة - وضع العرض
	# ---------------------------------------------------------------

	def _getSelectedSoftwareItem(self):
		"""إرجاع (group, category, software, url, url2) للعنصر المحدد في قائمة البرامج"""
		index = self.softwareList.GetSelection()
		if index == wx.NOT_FOUND:
			return None
		clientData = self.softwareList.GetClientData(index)
		if not clientData:
			return None
		groupName, categoryName, softwareName = clientData
		info = self.data.get(groupName, {}).get(categoryName, {}).get(softwareName, {})
		url = info.get("url", "")
		url2 = info.get("url2", "")

		# مزامنة تحديد Group وCategory تلقائياً حتى لو تم الوصول للبرنامج
		# مباشرة عبر البحث
		groupIndex = self.groupList.FindString(groupName)
		if groupIndex != wx.NOT_FOUND:
			self.groupList.SetSelection(groupIndex)

		return groupName, categoryName, softwareName, url, url2

	def _buildCopyBlock(self, name, url, url2):
		"""بناء نص النسخ لبرنامج واحد: الاسم، ثم الرابط الأساسي، ثم الرابط
		الإضافي إن وُجد، كل واحد بسطر مستقل. الملاحظات لا تُنسخ أبداً."""
		lines = [name, url]
		if url2:
			lines.append(url2)
		return "\n".join(lines)

	def _copySelectedAndClose(self):
		item = self._getSelectedSoftwareItem()
		if not item:
			ui.message(tr("msgNoSoftwareSelected"))
			return
		groupName, categoryName, softwareName, url, url2 = item
		if not url:
			ui.message(tr("msgNoLink"))
			return
		api.copyToClip(self._buildCopyBlock(softwareName, url, url2))
		ui.message(tr("msgCopied"))
		self.Close()

	def _openSelectedLink(self):
		item = self._getSelectedSoftwareItem()
		if not item:
			ui.message(tr("msgNoSoftwareSelected"))
			return
		groupName, categoryName, softwareName, url, url2 = item
		if not url:
			ui.message(tr("msgNoLink"))
			return
		webbrowser.open(url)
		ui.message(tr("msgOpeningLink"))

	def _writeClipboard(self):
		blocks = [self._buildCopyBlock(name, url, url2) for name, url, url2 in self.copiedItems]
		api.copyToClip("\n\n".join(blocks))


# =====================================================================
# صفحة إعدادات لغة الإضافة داخل NVDA Settings
# =====================================================================

class QadreenSettingsPanel(gui.settingsDialogs.SettingsPanel):
	# اسم الفئة يبقى "Qadreen" ثابتاً بغض النظر عن اللغة، فهو اسم العلامة
	title = "Qadreen"

	def makeSettings(self, settingsSizer):
		sizerHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)

		self._languageOptions = ["follow", "ar", "en"]
		choices = [
			tr("settingsFollowNVDA"),
			tr("settingsAlwaysArabic"),
			tr("settingsAlwaysEnglish"),
		]

		self.languageChoice = sizerHelper.addLabeledControl(
			tr("settingsLanguageLabel"),
			wx.Choice,
			choices=choices
		)

		currentValue = config.conf["qadreen"]["language"]
		try:
			currentIndex = self._languageOptions.index(currentValue)
		except ValueError:
			currentIndex = 0
		self.languageChoice.SetSelection(currentIndex)

		self.contactButton = sizerHelper.addItem(
			wx.Button(self, label=tr("contactDeveloperButton"))
		)
		self.contactButton.Bind(wx.EVT_BUTTON, self.onContactDeveloper)

	def onContactDeveloper(self, event):
		email = "saedmohamed.n2210@gmail.com"
		subject = urllib.parse.quote("Qadreen")
		webbrowser.open("mailto:{}?subject={}".format(email, subject))

	def onSave(self):
		selectedIndex = self.languageChoice.GetSelection()
		if selectedIndex != wx.NOT_FOUND:
			config.conf["qadreen"]["language"] = self._languageOptions[selectedIndex]


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	scriptCategory = "Qadreen"

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		restoreDataBackupIfNeeded()
		self.data = loadData()
		self._dialog = None
		self._helpDialog = None
		if QadreenSettingsPanel not in gui.NVDASettingsDialog.categoryClasses:
			gui.NVDASettingsDialog.categoryClasses.append(QadreenSettingsPanel)
		threading.Thread(target=checkForUpdateInBackground, daemon=True).start()

	@script(
		# الوصف يُبنى ديناميكياً باللغة الحالية عند تسجيل الاختصار في Input Gestures
		description=STRINGS["scriptDescription"]["ar"],
		gesture="kb:NVDA+control+q"
	)
	def script_openQuickSearch(self, gesture):
		if self._dialog is not None:
			try:
				self._dialog.Raise()
				return
			except RuntimeError:
				self._dialog = None

		# إعادة تحميل البيانات من الملف في كل مرة تفتح فيها النافذة
		self.data = loadData()

		parentWindow = wx.GetApp().TopWindow if wx.GetApp() else None
		self._dialog = SearchDialog(parentWindow, self.data)
		self._dialog.Bind(wx.EVT_CLOSE, self._onDialogClose)
		self._dialog.Show()
		wx.CallAfter(self._dialog.searchCtrl.SetFocus)

	def _onDialogClose(self, event):
		if self._dialog is not None:
			self._dialog.Destroy()
			self._dialog = None

	@script(
		description="فتح نافذة مساعدة الإضافة",
		gesture="kb:NVDA+control+h"
	)
	def script_openHelp(self, gesture):
		if self._helpDialog is not None:
			try:
				self._helpDialog.Raise()
				return
			except RuntimeError:
				self._helpDialog = None

		parentWindow = wx.GetApp().TopWindow if wx.GetApp() else None
		self._helpDialog = HelpDialog(parentWindow)
		self._helpDialog.Bind(wx.EVT_CLOSE, self._onHelpDialogClose)
		self._helpDialog.Show()
		wx.CallAfter(self._helpDialog.textCtrl.SetFocus)

	def _onHelpDialogClose(self, event):
		if self._helpDialog is not None:
			self._helpDialog.Destroy()
			self._helpDialog = None

	@script(
		description="إضافة رابط سريع من الحافظة إلى إضافة قادرين",
		gesture="kb:NVDA+shift+c"
	)
	def script_quickAddFromClipboard(self, gesture):
		try:
			clipboardText = api.getClipData().strip()
		except Exception:
			clipboardText = ""
		if not clipboardText:
			ui.message(tr("msgClipboardEmpty"))
			return

		wasAlreadyOpen = self._dialog is not None
		if self._dialog is None:
			self.data = loadData()
			parentWindow = wx.GetApp().TopWindow if wx.GetApp() else None
			self._dialog = SearchDialog(parentWindow, self.data, startMode="design")
			self._dialog.Bind(wx.EVT_CLOSE, self._onDialogClose)
			self._dialog.Show()
		elif self._dialog.mode != "design":
			self._dialog._toggleMode()

		wx.CallAfter(self._dialog.runQuickAdd, clipboardText, not wasAlreadyOpen)

	def terminate(self, *args, **kwargs):
		super().terminate(*args, **kwargs)
		if QadreenSettingsPanel in gui.NVDASettingsDialog.categoryClasses:
			gui.NVDASettingsDialog.categoryClasses.remove(QadreenSettingsPanel)

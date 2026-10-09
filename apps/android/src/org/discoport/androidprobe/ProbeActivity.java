package org.discoport.androidprobe;

import android.app.Activity;
import android.app.ActivityManager;
import android.os.Build;
import android.os.Bundle;
import android.util.Log;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import org.json.JSONObject;
import org.json.JSONArray;
import java.io.File;
import java.io.FileOutputStream;
import java.nio.charset.StandardCharsets;

/** Original capability/CPU probe. No Unity initialization or gameplay. */
public final class ProbeActivity extends Activity {
    static { System.loadLibrary("discoprobe"); }
    private static native String nativeReport(android.content.res.AssetManager assets, String dataDirectory);

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        LinearLayout panel = new LinearLayout(this);
        panel.setOrientation(LinearLayout.VERTICAL);
        int padding = (int)(24 * getResources().getDisplayMetrics().density);
        panel.setPadding(padding, padding, padding, padding);
        TextView title = new TextView(this);
        title.setText("Disco Android Probe\nDevice and CPU diagnostics — gameplay is not integrated");
        title.setTextSize(22);
        panel.addView(title);
        TextView output = new TextView(this);
        output.setTextSize(16);
        output.setTextIsSelectable(true);
        output.setText("Checking native CPU and Vulkan capabilities…");
        panel.addView(output);
        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        scroll.addView(panel);
        setContentView(scroll);
        new Thread(() -> {
            String report;
            try {
                File metadataRoot = new File(getFilesDir(), "NativeMetadata");
                File metadataFolder = new File(metadataRoot, "Metadata");
                metadataFolder.mkdirs();
                try (java.io.InputStream input = getAssets().open("global-metadata.dat");
                     FileOutputStream destination = new FileOutputStream(new File(metadataFolder, "global-metadata.dat"))) {
                    byte[] buffer = new byte[65536]; int length;
                    while ((length = input.read(buffer)) != -1) destination.write(buffer, 0, length);
                } catch (java.io.FileNotFoundException absent) { /* Capability-only build. */ }
                JSONObject data = new JSONObject(nativeReport(getAssets(), metadataRoot.getAbsolutePath()));
                data.put("scope", "Device, shader and selected native runtime diagnostics; not Unity/gameplay");
                data.put("model", Build.MODEL);
                data.put("manufacturer", Build.MANUFACTURER);
                data.put("sdk", Build.VERSION.SDK_INT);
                data.put("abis", new JSONArray(Build.SUPPORTED_ABIS));
                ActivityManager manager = (ActivityManager)getSystemService(ACTIVITY_SERVICE);
                ActivityManager.MemoryInfo memory = new ActivityManager.MemoryInfo();
                manager.getMemoryInfo(memory);
                data.put("physical_memory_bytes", memory.totalMem);
                data.put("system_available_memory_bytes", memory.availMem);
                data.put("java_heap_class_mib", manager.getMemoryClass());
                data.put("memory_note", "Physical/system memory and Java heap class are not the native process budget");
                data.put("display_width_px", getResources().getDisplayMetrics().widthPixels);
                data.put("display_height_px", getResources().getDisplayMetrics().heightPixels);
                report = data.toString(2);
                try (FileOutputStream file = new FileOutputStream(new File(getFilesDir(), "capabilities.json"))) {
                    file.write(report.getBytes(StandardCharsets.UTF_8));
                }
                Log.i("DiscoAndroidProbe", report);
            } catch (Exception error) {
                report = "Probe failed: " + error;
                Log.e("DiscoAndroidProbe", report);
            }
            final String message = report;
            runOnUiThread(() -> output.setText(message));
        }, "Disco capability probe").start();
    }
}

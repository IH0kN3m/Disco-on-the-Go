package org.discoport.androidgame;

import android.os.Bundle;
import android.view.MotionEvent;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import com.unity3d.player.UnityPlayerActivity;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;

/** Original local-data bootstrap; Unity owns rendering and Android input. */
public final class GameActivity extends UnityPlayerActivity {
    private static native void prepareRuntime(android.content.res.AssetManager assets, String path, String gamePath);
    private static native void pinch(int phase, double scale, int first, int second, float x1, float y1, float x2, float y2);
    private static native boolean highlightAllowed();
    private VirtualGamepad pad;
    private static native void highlight(boolean down);
    static native void padEnabled(boolean enabled);
    static native void padButton(int button, boolean down);
    static native void padAxis(int stick, float x, float y);
    private boolean suppressTouches;
    private double pinchScale = 1;
    private int firstPointer, secondPointer;
    private float x1,y1,x2,y2;
    private final Handler gestures = new Handler(Looper.getMainLooper());
    private boolean highlighting;
    private long highlightDownTime;
    private final Runnable hold = new Runnable() {
        @Override public void run() {
            if (!suppressTouches) { setHighlight(false); return; }
            setHighlight(highlightAllowed());
            gestures.postDelayed(this, 50);
        }
    };
    private void sendPinch(int phase) { pinch(phase,pinchScale,firstPointer,secondPointer,x1,y1,x2,y2); }
    private void setHighlight(boolean down) {
        if (down == highlighting) return;
        highlighting = down;
        highlight(down);
    }
    private void cancelGesture() {
        gestures.removeCallbacks(hold);setHighlight(false);sendPinch(0);
        suppressTouches=false;
    }
    @Override protected String updateUnityCommandLineArguments(String arguments) {
        return (arguments == null ? "" : arguments) + " -force-gles32";
    }
    @Override protected void onCreate(Bundle state) {
        try {
            File root = new File(getFilesDir(), "NativeMetadata");
            File folder = new File(root, "Metadata");
            if (!folder.isDirectory() && !folder.mkdirs()) throw new IllegalStateException("Cannot create metadata directory");
            try (InputStream input = getAssets().open("global-metadata.dat");
                 FileOutputStream output = new FileOutputStream(new File(folder, "global-metadata.dat"))) {
                byte[] bytes = new byte[65536]; int count;
                while ((count = input.read(bytes)) != -1) output.write(bytes, 0, count);
            }
            File resources = new File(root, "Resources");
            if (!resources.isDirectory() && !resources.mkdirs()) throw new IllegalStateException("Cannot create runtime resources directory");
            for (String name : getAssets().list("runtime-resources")) {
                if (!name.matches("[A-Za-z0-9.]+-resources\\.dat")) throw new IllegalStateException("Unexpected runtime resource name");
                try (InputStream input = getAssets().open("runtime-resources/" + name);
                     FileOutputStream output = new FileOutputStream(new File(resources, name))) {
                    byte[] bytes = new byte[65536]; int count;
                    while ((count = input.read(bytes)) != -1) output.write(bytes, 0, count);
                }
            }
            System.loadLibrary("il2cpp");
            File game = new File(getExternalFilesDir(null), "GameFiles");
            if (!game.isDirectory() && !game.mkdirs()) throw new IllegalStateException("Cannot create game directory");
            prepareRuntime(getAssets(), root.getAbsolutePath(), game.getAbsolutePath());
        } catch (Exception error) { throw new IllegalStateException("Local runtime preparation failed", error); }
        super.onCreate(state);
        pad=new VirtualGamepad(this);
        addContentView(pad,new android.view.ViewGroup.LayoutParams(-1,-1));
    }
    @Override public boolean dispatchTouchEvent(MotionEvent event) {
        if (pad == null) return super.dispatchTouchEvent(event);
        if (pad.handle(event)) { cancelGesture();return true; }
        if (event.getPointerCount() >= 2 && !suppressTouches) {
            firstPointer=event.getPointerId(0);secondPointer=event.getPointerId(1);
            float width=Math.max(1,getWindow().getDecorView().getWidth()),height=Math.max(1,getWindow().getDecorView().getHeight());
            x1=event.getX(0)/width;y1=event.getY(0)/height;x2=event.getX(1)/width;y2=event.getY(1)/height;
            MotionEvent cancel=MotionEvent.obtain(event);cancel.setAction(MotionEvent.ACTION_CANCEL);
            super.dispatchTouchEvent(cancel);cancel.recycle();
            suppressTouches=true;pinchScale=1;sendPinch(1);gestures.postDelayed(hold,350);
        }
        if (suppressTouches) {
            if (event.getActionMasked()==MotionEvent.ACTION_POINTER_UP) {gestures.removeCallbacks(hold);setHighlight(false);sendPinch(0);}
            if (event.getActionMasked()==MotionEvent.ACTION_UP||event.getActionMasked()==MotionEvent.ACTION_CANCEL) cancelGesture();
            return true;
        }
        return super.dispatchTouchEvent(event);
    }
    @Override protected void onPause() {
        cancelGesture();
        if(pad!=null)pad.reset();
        super.onPause();
    }
    @Override public void onWindowFocusChanged(boolean focus) {
        if (!focus && pad != null) {cancelGesture();pad.reset();}
        super.onWindowFocusChanged(focus);
    }
}

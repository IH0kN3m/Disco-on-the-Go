package org.discoport.androidprobe;

import android.app.Instrumentation;
import android.os.Bundle;
import android.os.SystemClock;
import android.view.MotionEvent;
import android.view.InputDevice;
import android.view.WindowManager;
import android.util.DisplayMetrics;
import android.graphics.Bitmap;
import java.io.File;
import java.io.FileOutputStream;

/** Original bounded two-finger device test; leaves the foreground game process intact. */
public final class GestureInstrumentation extends Instrumentation {
    private Bundle arguments;
    private long downTime;
    private int width,height;
    private String stage="setup";
    @Override public void onCreate(Bundle arguments) { this.arguments=arguments;start(); }
    private void capture(String name) throws Exception {
        Bitmap bitmap=getUiAutomation().takeScreenshot();
        if (bitmap==null) throw new IllegalStateException("Screenshot unavailable");
        if (name.equals("gesture-before.png")) { width=bitmap.getWidth();height=bitmap.getHeight(); }
        try (FileOutputStream stream=new FileOutputStream(new File(getTargetContext().getFilesDir(),name))) {
            if (!bitmap.compress(Bitmap.CompressFormat.PNG,100,stream)) throw new IllegalStateException("Screenshot failed");
        } finally { bitmap.recycle(); }
    }
    private void event(int action,int count,float span) {
        MotionEvent.PointerProperties[] properties=new MotionEvent.PointerProperties[count];
        MotionEvent.PointerCoords[] coordinates=new MotionEvent.PointerCoords[count];
        for(int i=0;i<count;++i) {
            properties[i]=new MotionEvent.PointerProperties();properties[i].id=i;properties[i].toolType=MotionEvent.TOOL_TYPE_FINGER;
            coordinates[i]=new MotionEvent.PointerCoords();coordinates[i].x=width*(.28f+(i==0?-span:span));
            coordinates[i].y=height*.55f;coordinates[i].pressure=1;coordinates[i].size=.05f;
        }
        MotionEvent event=MotionEvent.obtain(downTime,SystemClock.uptimeMillis(),action,count,properties,coordinates,0,0,1,1,0,0,InputDevice.SOURCE_TOUCHSCREEN,0);
        try { if(!getUiAutomation().injectInputEvent(event,false)) throw new IllegalStateException("Input injection failed action="+action+" viewport="+width+"x"+height); }
        finally { event.recycle(); }
    }
    @Override public void onStart() {
        Bundle result=new Bundle();boolean down=false;
        try {
            String mode=arguments.getString("gesture","pinch");
            if(!mode.equals("pinch")&&!mode.equals("hold"))throw new IllegalArgumentException("gesture must be pinch or hold");
            DisplayMetrics metrics=new DisplayMetrics();
            ((WindowManager)getTargetContext().getSystemService("window")).getDefaultDisplay().getRealMetrics(metrics);
            width=metrics.widthPixels;height=metrics.heightPixels;
            capture("gesture-before.png");downTime=SystemClock.uptimeMillis();
            stage="first finger";event(MotionEvent.ACTION_DOWN,1,.08f);down=true;SystemClock.sleep(60);
            stage="second finger";
            event(MotionEvent.ACTION_POINTER_DOWN|(1<<MotionEvent.ACTION_POINTER_INDEX_SHIFT),2,.08f);
            float span=.08f;
            stage="movement";for(int i=0;i<40;++i){if(mode.equals("pinch"))span=.08f+.08f*i/39;event(MotionEvent.ACTION_MOVE,2,span);SystemClock.sleep(20);}
            capture("gesture-during.png");
            event(MotionEvent.ACTION_POINTER_UP|(1<<MotionEvent.ACTION_POINTER_INDEX_SHIFT),2,span);
            event(MotionEvent.ACTION_UP,1,span);down=false;SystemClock.sleep(300);capture("gesture-after.png");
            result.putString("result","gesture delivered; inspect Unity logs and private screenshots for game behavior");finish(0,result);
        } catch(Exception error) {
            if(down)try{event(MotionEvent.ACTION_CANCEL,2,.08f);}catch(Exception ignored){}
            result.putString("error",stage+": "+error.toString());finish(1,result);
        }
    }
}

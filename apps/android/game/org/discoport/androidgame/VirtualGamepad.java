package org.discoport.androidgame;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.RectF;
import android.view.MotionEvent;
import android.view.View;
import java.util.ArrayList;
import java.util.HashMap;

/** Original vector gamepad overlay. Empty areas pass through to the game. */
final class VirtualGamepad extends View {
    private final Paint paint=new Paint(3);
    private final ArrayList<Control> controls=new ArrayList<>();
    private final HashMap<Integer,Control> pointers=new HashMap<>();
    private boolean shown;
    private float iconX=1,iconY=-1;
    private float unit=1,leftX,leftY,rightX,rightY;
    private float leftDx,leftDy,rightDx,rightDy;
    private int oldWidth,oldHeight;
    private final RectF toggle=new RectF();
    private final RectF[] panels={new RectF(),new RectF()};
    private final float[] stickValues=new float[4];
    private static class Control {
        final int kind,index,panel;final RectF bounds;
        float previousX,previousY,startX,startY;boolean dragged;
        Control(int kind,int index,int panel,RectF bounds){this.kind=kind;this.index=index;this.panel=panel;this.bounds=bounds;}
    }
    VirtualGamepad(Context context){super(context);iconX=context.getSharedPreferences("touch-controls",0).getFloat("icon-x",1);iconY=context.getSharedPreferences("touch-controls",0).getFloat("icon-y",-1);setWillNotDraw(false);setImportantForAccessibility(IMPORTANT_FOR_ACCESSIBILITY_NO);}
    private void add(int kind,int index,int panel,float x,float y,float w,float h){
        float ox=panel==0?leftX:rightX,oy=panel==0?leftY:rightY;
        controls.add(new Control(kind,index,panel,new RectF(ox+x*unit,oy+y*unit,ox+(x+w)*unit,oy+(y+h)*unit)));
    }
    private void layoutControls(){
        if(getWidth()<=0||getHeight()<=0)return;
        float density=getResources().getDisplayMetrics().density;
        unit=Math.min(density,Math.min(getWidth()/700f,getHeight()/420f));
        if(oldWidth!=getWidth()||oldHeight!=getHeight()) {leftDx=leftDy=rightDx=rightDy=0;oldWidth=getWidth();oldHeight=getHeight();}
        leftX=Math.max(8*unit,Math.min(getWidth()-280*unit,18*unit+leftDx));
        rightX=Math.max(8*unit,Math.min(getWidth()-318*unit,getWidth()-336*unit+rightDx));
        leftY=Math.max(60*unit,Math.min(getHeight()-238*unit,getHeight()-320*unit+leftDy));
        rightY=Math.max(60*unit,Math.min(getHeight()-238*unit,getHeight()-320*unit+rightDy));
        panels[0].set(leftX,leftY,leftX+270*unit,leftY+225*unit);
        panels[1].set(rightX,rightY,rightX+316*unit,rightY+225*unit);
        float iconLeft=8*unit+Math.max(0,Math.min(1,iconX))*(getWidth()-58*unit);
        float iconTop=iconY<0?60*unit:8*unit+Math.max(0,Math.min(1,iconY))*(getHeight()-54*unit);
        toggle.set(iconLeft,iconTop,iconLeft+42*unit,iconTop+38*unit);
        controls.clear();
        add(0,0,0,0,60,135,135);add(0,1,1,0,90,120,120);
        add(1,4,0,0,0,60,42);add(1,6,0,68,0,60,42);
        add(1,5,1,188,0,60,42);add(1,7,1,256,0,60,42);
        add(1,0,1,212,154,50,50);add(1,1,1,266,100,50,50);
        add(1,2,1,158,100,50,50);add(1,3,1,212,46,50,50);add(1,8,1,76,0,60,42);
        add(1,9,0,178,102,38,38);add(1,10,0,178,178,38,38);
        add(1,11,0,140,140,38,38);add(1,12,0,216,140,38,38);
    }
    void reset(){
        for(Control control:pointers.values())release(control);
        pointers.clear();for(int i=0;i<4;++i)stickValues[i]=0;
        GameActivity.padEnabled(false);if(shown)GameActivity.padEnabled(true);invalidate();
    }
    private void release(Control control){
        if(control.kind==0){GameActivity.padAxis(control.index,0,0);stickValues[2*control.index]=stickValues[2*control.index+1]=0;}
        if(control.kind==1)GameActivity.padButton(control.index,false);
    }
    private void update(Control control,float x,float y){
        if(control.kind==0){
            float radius=control.bounds.width()*.3f;
            float dx=(x-control.bounds.centerX())/radius,dy=(control.bounds.centerY()-y)/radius;
            float length=(float)Math.hypot(dx,dy);
            if(length<.08f){dx=dy=0;}else if(length>1){dx/=length;dy/=length;}
            stickValues[2*control.index]=dx;stickValues[2*control.index+1]=dy;
            GameActivity.padAxis(control.index,dx,dy);
        }else if(control.kind==2){
            if(Math.hypot(x-control.startX,y-control.startY)>8*unit)control.dragged=true;
            if(control.dragged){
                float left=Math.max(8*unit,Math.min(getWidth()-50*unit,toggle.left+x-control.previousX));
                float top=Math.max(8*unit,Math.min(getHeight()-46*unit,toggle.top+y-control.previousY));
                iconX=(left-8*unit)/Math.max(1,getWidth()-58*unit);
                iconY=(top-8*unit)/Math.max(1,getHeight()-54*unit);layoutControls();
            }
            control.previousX=x;control.previousY=y;
        }
    }
    boolean handle(MotionEvent event){
        layoutControls();int action=event.getActionMasked(),index=event.getActionIndex();
        boolean consumed=!pointers.isEmpty();
        if(action==MotionEvent.ACTION_DOWN||action==MotionEvent.ACTION_POINTER_DOWN){
            float x=event.getX(index),y=event.getY(index);Control hit=null;
            if(toggle.contains(x,y))hit=new Control(2,0,0,toggle);
            else if(shown){for(Control control:controls)if(control.bounds.contains(x,y)){hit=control;break;}}
            if(hit!=null){
                boolean owned=false;for(Control control:pointers.values())if(control.kind==hit.kind&&control.index==hit.index&&control.panel==hit.panel)owned=true;
                if(!owned){hit.previousX=hit.startX=x;hit.previousY=hit.startY=y;pointers.put(event.getPointerId(index),hit);
                    if(hit.kind==1)GameActivity.padButton(hit.index,true);update(hit,x,y);}
                consumed=true;
            }
        }else if(action==MotionEvent.ACTION_MOVE){
            for(int i=0;i<event.getPointerCount();++i){Control control=pointers.get(event.getPointerId(i));if(control!=null)update(control,event.getX(i),event.getY(i));}
        }else if(action==MotionEvent.ACTION_UP||action==MotionEvent.ACTION_POINTER_UP){
            Control control=pointers.remove(event.getPointerId(index));
            if(control!=null){release(control);
                if(control.kind==2){if(!control.dragged&&toggle.contains(event.getX(index),event.getY(index))){reset();shown=!shown;GameActivity.padEnabled(shown);}getContext().getSharedPreferences("touch-controls",0).edit().putFloat("icon-x",iconX).putFloat("icon-y",iconY).apply();}
                consumed=true;}
        }else if(action==MotionEvent.ACTION_CANCEL){reset();}
        if(consumed)invalidate();return consumed;
    }
    private void background(Canvas canvas,RectF rect){paint.setColor(0xa60c0c0c);paint.setStyle(Paint.Style.FILL);canvas.drawRoundRect(rect,12*unit,12*unit,paint);}
    private void text(Canvas canvas,RectF rect,String text,int color){paint.setColor(color);paint.setTextSize(18*unit);paint.setTextAlign(Paint.Align.CENTER);canvas.drawText(text,rect.centerX(),rect.centerY()+6*unit,paint);}
    @Override protected void onDraw(Canvas canvas){
        layoutControls();background(canvas,toggle);paint.setColor(shown?0xff8ce0b0:0xffffffff);paint.setStyle(Paint.Style.STROKE);paint.setStrokeWidth(2*unit);
        RectF icon=new RectF(toggle.left+8*unit,toggle.top+10*unit,toggle.right-8*unit,toggle.bottom-10*unit);canvas.drawRoundRect(icon,5*unit,5*unit,paint);
        canvas.drawLine(icon.left+4*unit,icon.centerY(),icon.left+10*unit,icon.centerY(),paint);canvas.drawLine(icon.left+7*unit,icon.centerY()-3*unit,icon.left+7*unit,icon.centerY()+3*unit,paint);
        canvas.drawCircle(icon.right-5*unit,icon.centerY()-2*unit,1.2f*unit,paint);canvas.drawCircle(icon.right-8*unit,icon.centerY()+2*unit,1.2f*unit,paint);
        if(!shown)return;
        String[] labels={"A","B","X","Y","LB","RB","LT","RT","≡","↑","↓","←","→"};
        int[] colors={0xff6bdc86,0xfff07474,0xff78afff,0xfff1d266};
        for(Control control:controls){
            if(control.kind==0){paint.setStyle(Paint.Style.FILL);paint.setColor(0x80101010);canvas.drawOval(control.bounds,paint);paint.setColor(0x90ffffff);
                float r=control.bounds.width()*.3f,x=control.bounds.centerX()+stickValues[2*control.index]*r,y=control.bounds.centerY()-stickValues[2*control.index+1]*r;
                canvas.drawCircle(x,y,19*unit,paint);
            }else {background(canvas,control.bounds);text(canvas,control.bounds,labels[control.index],control.index<4?colors[control.index]:0xffffffff);}
        }
    }
}

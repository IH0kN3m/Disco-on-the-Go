using System;
using UnityEditor;
using UnityEditor.Android;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;

public static class ExportAndroidHost
{
    public static void Export()
    {
        if (Application.unityVersion != "2020.3.12f1") throw new InvalidOperationException("Unexpected Unity version");
        AndroidExternalToolsSettings.sdkRootPath = Environment.GetEnvironmentVariable("DISCO_ANDROID_SDK");
        AndroidExternalToolsSettings.ndkRootPath = Environment.GetEnvironmentVariable("DISCO_ANDROID_NDK");
        AndroidExternalToolsSettings.jdkRootPath = Environment.GetEnvironmentVariable("DISCO_ANDROID_JDK");
        var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
        var camera = new GameObject("Host camera").AddComponent<Camera>();
        camera.clearFlags = CameraClearFlags.SolidColor;
        camera.backgroundColor = new Color(0.08f, 0.12f, 0.17f);
        EditorSceneManager.SaveScene(scene, "Assets/Host.unity");
        PlayerSettings.companyName = "Disco Port";
        PlayerSettings.productName = "Disco Android Host";
        PlayerSettings.SetApplicationIdentifier(BuildTargetGroup.Android, "org.discoport.androidgame");
        PlayerSettings.SetScriptingBackend(BuildTargetGroup.Android, ScriptingImplementation.IL2CPP);
        PlayerSettings.Android.targetArchitectures = AndroidArchitecture.ARM64;
        PlayerSettings.Android.minSdkVersion = (AndroidSdkVersions)28;
        PlayerSettings.Android.targetSdkVersion = (AndroidSdkVersions)30;
        PlayerSettings.stripEngineCode = false;
        PlayerSettings.SetUseDefaultGraphicsAPIs(BuildTarget.Android, false);
        PlayerSettings.SetGraphicsAPIs(BuildTarget.Android, new[] { GraphicsDeviceType.OpenGLES3 });
        PlayerSettings.defaultInterfaceOrientation = UIOrientation.LandscapeLeft;
        PlayerSettings.Android.blitType = AndroidBlitType.Always;
        EditorUserBuildSettings.exportAsGoogleAndroidProject = true;
        var report = BuildPipeline.BuildPlayer(new BuildPlayerOptions {
            scenes = new[] { "Assets/Host.unity" },
            locationPathName = Environment.GetEnvironmentVariable("DISCO_ANDROID_EXPORT"),
            target = BuildTarget.Android,
            options = BuildOptions.Development
        });
        if (report.summary.result != BuildResult.Succeeded) throw new InvalidOperationException("Android host export failed");
        Debug.Log("DISCO_ANDROID_EXPORT_SUCCEEDED");
    }
}

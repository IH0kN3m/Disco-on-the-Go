using System;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;

public static class ExportIPadHost
{
    public static void ExportIOS()
    {
        if (Application.unityVersion != "2020.3.12f1") throw new InvalidOperationException("Expected Unity 2020.3.12f1");
        var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
        EditorSceneManager.SaveScene(scene, "Assets/Host.unity");
        PlayerSettings.productName = "Disco on the Go";
        PlayerSettings.companyName = "Disco on the Go";
        PlayerSettings.SetApplicationIdentifier(BuildTargetGroup.iOS, "org.discoport.engineprobe");
        PlayerSettings.SetScriptingBackend(BuildTargetGroup.iOS, ScriptingImplementation.IL2CPP);
        PlayerSettings.SetArchitecture(BuildTargetGroup.iOS, 1);
        PlayerSettings.iOS.targetDevice = iOSTargetDevice.iPadOnly;
        PlayerSettings.iOS.targetOSVersionString = "17.0";
        PlayerSettings.SetUseDefaultGraphicsAPIs(BuildTarget.iOS, false);
        PlayerSettings.SetGraphicsAPIs(BuildTarget.iOS, new[] { GraphicsDeviceType.Metal });
        PlayerSettings.defaultInterfaceOrientation = UIOrientation.LandscapeLeft;
        PlayerSettings.iOS.appleEnableAutomaticSigning = true;
        var team = Environment.GetEnvironmentVariable("UNITY_DEVELOPMENT_TEAM");
        if (!String.IsNullOrEmpty(team)) PlayerSettings.iOS.appleDeveloperTeamID = team;
        var output = Environment.GetEnvironmentVariable("UNITY_IOS_OUTPUT");
        if (String.IsNullOrEmpty(output)) throw new InvalidOperationException("UNITY_IOS_OUTPUT must point under artifacts");
        var report = BuildPipeline.BuildPlayer(new BuildPlayerOptions {
            scenes = new[] { "Assets/Host.unity" }, locationPathName = output,
            target = BuildTarget.iOS, options = BuildOptions.Development
        });
        if (report.summary.result != BuildResult.Succeeded) throw new InvalidOperationException("Unity iOS export failed: " + report.summary.result);
        Debug.Log("Disco on the Go iOS export succeeded");
    }
}
